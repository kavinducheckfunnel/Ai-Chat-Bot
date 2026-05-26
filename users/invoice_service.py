"""Invoice generation, rendering, and emailing.

Composes an Invoice from local data — does NOT depend on Stripe. The
subscription is billed by Stripe separately; this is the document the
tenant gets that summarises what they used + what was charged + what
add-ons they bought, for their records and ours.

Public API:
  generate_invoice(tenant, year, month, force=False) -> Invoice
  render_invoice_html(invoice) -> str
  email_invoice(invoice, to_email=None) -> bool
"""

from __future__ import annotations

import calendar
import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


# Default colour when a tenant has no client / no chosen brand colour.
# Matches the original Checkfunnel header gradient start point.
_DEFAULT_BRAND_COLOR = '#6366f1'

# `#RGB`, `#RRGGBB`, or `#RRGGBBAA` — anything else gets discarded so a
# malformed value never makes it into the rendered CSS gradient.
_HEX_COLOR_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')


def _safe_brand_color(value: str | None) -> str:
    """Return `value` if it parses as a hex colour, otherwise the default."""
    candidate = (value or '').strip()
    if candidate and _HEX_COLOR_RE.match(candidate):
        return candidate
    return _DEFAULT_BRAND_COLOR


def _lighten_hex(color: str, amount: float = 0.20) -> str:
    """Move `color` toward white by `amount` (0..1). Used to build the
    second stop of the header gradient when only one brand colour is set.

    Always returns a valid `#RRGGBB` string — falls back to the default
    on any parse error.
    """
    base = _safe_brand_color(color).lstrip('#')
    if len(base) == 3:
        base = ''.join(c * 2 for c in base)
    elif len(base) == 8:
        base = base[:6]
    try:
        r = int(base[0:2], 16)
        g = int(base[2:4], 16)
        b = int(base[4:6], 16)
    except ValueError:
        base = _DEFAULT_BRAND_COLOR.lstrip('#')
        r = int(base[0:2], 16); g = int(base[2:4], 16); b = int(base[4:6], 16)

    amount = max(0.0, min(1.0, amount))
    r = round(r + (255 - r) * amount)
    g = round(g + (255 - g) * amount)
    b = round(b + (255 - b) * amount)
    return f'#{r:02x}{g:02x}{b:02x}'


def _primary_client(tenant):
    """The Client we treat as the tenant's brand source.

    A tenant can have multiple Client rows (one per managed website).
    Invoice branding pulls from whichever was created first — almost
    always the only one. Returns None if the tenant has no clients.
    """
    return tenant.clients.order_by('id').first() if tenant else None


def _period_bounds(year: int, month: int) -> tuple[date, date]:
    """Inclusive month boundaries (e.g. 2026-05 → 2026-05-01 .. 2026-05-31)."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _next_invoice_number(tenant, year: int, month: int) -> str:
    """CF-{tenant_id:04d}-{YYYYMM}-{seq:02d}. seq is ordinal for that month."""
    from users.models import Invoice
    prefix = f'CF-{tenant.pk:04d}-{year}{month:02d}'
    seq = Invoice.objects.filter(invoice_number__startswith=prefix).count() + 1
    return f'{prefix}-{seq:02d}'


def _gather_usage_summary(tenant, period_start: date, period_end: date) -> dict:
    """Roll up everything the tenant did this month so the invoice tells a
    story, not just lists prices. None of this is BILLED — it's context.
    """
    from chat.models import ChatSession
    client_ids = list(tenant.clients.values_list('id', flat=True))

    sessions_qs = ChatSession.objects.filter(
        client_id__in=client_ids,
        created_at__date__gte=period_start,
        created_at__date__lte=period_end,
    )
    active = sessions_qs.filter(message_count__gte=1)

    # Count outcomes — these came from E1 tagging
    outcomes = {
        row['outcome']: row['n']
        for row in sessions_qs.values('outcome').annotate(n=Count('session_id'))
    }

    # Leads: any session with email OR phone captured (excluding empty)
    leads = sessions_qs.filter(
        Q(lead_email__isnull=False) | Q(lead_phone__isnull=False)
    ).exclude(lead_email='').count()

    # Hot leads (kanban_state == HOT_LEAD or CONVERTED)
    hot_leads = sessions_qs.filter(kanban_state__in=['HOT_LEAD', 'CONVERTED']).count()

    # Total AI messages = sum of message_count across sessions
    total_msgs = sessions_qs.aggregate(s=Sum('message_count'))['s'] or 0

    # Top 3 pages by visit count (across all sessions in period)
    top_pages = []
    try:
        from analytics.models import ActivityEvent
        page_rows = (
            ActivityEvent.objects
            .filter(client_id__in=client_ids,
                    created_at__date__gte=period_start,
                    created_at__date__lte=period_end,
                    event_type='page_view')
            .values('page_url')
            .annotate(n=Count('id'))
            .order_by('-n')[:3]
        )
        top_pages = [{'url': r['page_url'], 'views': r['n']} for r in page_rows]
    except Exception:
        # analytics app may not be importable in some test paths; tolerate
        pass

    return {
        'sessions_total':   sessions_qs.count(),
        'sessions_active':  active.count(),
        'sessions_ghost':   outcomes.get('ghost', 0),
        'leads':            leads,
        'hot_leads':        hot_leads,
        'converted':        outcomes.get('converted', 0),
        'abandoned':        outcomes.get('abandoned', 0),
        'escalated':        outcomes.get('escalated', 0),
        'ai_messages':      total_msgs,
        'images':           tenant.images_this_month or 0,
        'voice':            tenant.voice_this_month or 0,
        'videos':           getattr(tenant, 'videos_this_month', 0) or 0,
        'top_pages':        top_pages,
    }


def _gather_line_items(tenant, period_start: date, period_end: date) -> list[dict]:
    """Compose billable line items: subscription + every add-on in period."""
    from users.models import AddOnPurchase
    items = []

    # Subscription line (always present if tenant has a plan)
    plan = tenant.plan
    if plan and plan.price_monthly and float(plan.price_monthly) > 0:
        interval = tenant.billing_interval or 'monthly'
        if interval == 'annual':
            # 15% annual discount per the billing page logic
            monthly_eq = float(plan.price_monthly) * 0.85
            desc = f'{plan.name} plan — {period_start.strftime("%B %Y")} (annual billing)'
            unit = f'{monthly_eq:.2f}'
        else:
            desc = f'{plan.name} plan — {period_start.strftime("%B %Y")}'
            unit = f'{float(plan.price_monthly):.2f}'
        items.append({
            'description': desc,
            'quantity': 1,
            'unit_price_usd': unit,
            'amount_usd': unit,
        })

    # Add-on purchases in this period
    addon_qs = AddOnPurchase.objects.filter(
        tenant=tenant,
        status='succeeded',
        completed_at__date__gte=period_start,
        completed_at__date__lte=period_end,
    )
    kind_label = {'message': 'AI message credits', 'image': 'Image upload credits',
                  'voice': 'Voice command credits', 'video': 'Video upload credits'}
    for purchase in addon_qs:
        items.append({
            'description': f'{kind_label.get(purchase.kind, purchase.kind)} — top-up (x{purchase.quantity})',
            'quantity': purchase.quantity,
            'unit_price_usd': f'{float(purchase.unit_price_usd):.4f}',
            'amount_usd': f'{float(purchase.total_paid_usd):.2f}',
        })
    return items


@transaction.atomic
def generate_invoice(tenant, year: int, month: int, force: bool = False, status: str = 'issued'):
    """Generate (or re-fetch) the invoice for a tenant + month.

    If an invoice already exists for the period:
      - returns it unchanged when force=False
      - regenerates fields when force=True (keeps invoice_number)
    """
    from users.models import Invoice
    period_start, period_end = _period_bounds(year, month)

    existing = Invoice.objects.filter(tenant=tenant, period_start=period_start).first()
    if existing and not force:
        return existing

    line_items = _gather_line_items(tenant, period_start, period_end)
    usage_summary = _gather_usage_summary(tenant, period_start, period_end)

    subtotal = sum(Decimal(item['amount_usd']) for item in line_items)
    tax_percent = Decimal('0')   # configurable later — per-tenant tax field could add this
    tax = (subtotal * tax_percent / Decimal('100')).quantize(Decimal('0.01'))
    total = (subtotal + tax).quantize(Decimal('0.01'))

    # Snapshot the tenant's first-client branding so historical invoices
    # don't get rewritten when the customer changes their logo months later.
    primary = _primary_client(tenant)
    brand_logo = (getattr(primary, 'chatbot_logo_url', '') or '') if primary else ''
    # Stored RAW: we render through _safe_brand_color so a junk value
    # never blows up the CSS gradient, but we keep the original string
    # for transparency in the DB.
    brand_color = (getattr(primary, 'chatbot_color', '') or '') if primary else ''

    fields = dict(
        tenant=tenant,
        period_start=period_start,
        period_end=period_end,
        plan_name_at_issue=(tenant.plan.name if tenant.plan else ''),
        company_name_at_issue=(tenant.company_name or tenant.user.username),
        recipient_email_at_issue=(tenant.user.email or ''),
        brand_logo_url_at_issue=brand_logo,
        brand_color_at_issue=brand_color,
        subtotal_usd=subtotal,
        tax_percent=tax_percent,
        tax_usd=tax,
        total_usd=total,
        line_items=line_items,
        usage_summary=usage_summary,
        status=status,
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.save()
        return existing

    invoice = Invoice(invoice_number=_next_invoice_number(tenant, year, month), **fields)
    invoice.save()
    return invoice


def render_invoice_html(invoice) -> str:
    """Render the invoice as a self-contained HTML document.

    Browser-printable to PDF via Cmd+P / Ctrl+P → Save as PDF.
    Inline CSS so it survives any email-client rewriting.
    """
    backend_url = getattr(settings, 'BACKEND_PUBLIC_URL', '') or 'https://ai.checkfunnels.com'

    # Build the header gradient from the brand colour stored at issue time.
    # `_safe_brand_color` gates anything not matching `#RGB`/`#RRGGBB`/`#RRGGBBAA`
    # so a typo in the tenant's settings can't render an invalid CSS gradient.
    brand_color = _safe_brand_color(invoice.brand_color_at_issue)
    brand_color_secondary = _lighten_hex(brand_color, 0.18)
    brand_logo_url = (invoice.brand_logo_url_at_issue or '').strip()

    return render_to_string('billing/invoice.html', {
        'invoice': invoice,
        'line_items': invoice.line_items or [],
        'usage': invoice.usage_summary or {},
        'tenant_name': invoice.company_name_at_issue,
        'recipient_email': invoice.recipient_email_at_issue,
        'backend_url': backend_url,
        'company_brand': 'Checkfunnel',
        'support_email': 'support@checkfunnels.com',
        'brand_logo_url': brand_logo_url,
        'brand_color': brand_color,
        'brand_color_secondary': brand_color_secondary,
    })


def render_invoice_pdf(invoice) -> bytes:
    """Render the invoice as a real PDF document via WeasyPrint.

    Imports WeasyPrint lazily so app startup doesn't pay the Cairo/Pango
    cost on every container restart, and so the module can be imported on
    machines without the system libraries installed (the underlying call
    will still error if it's actually used there).

    Returns the raw PDF bytes. The HTML template doubles as the PDF
    source — its print stylesheet lives in `@media print` blocks so the
    same `invoice.html` produces a clean letter-sized document.
    """
    from weasyprint import HTML  # local import — Cairo/Pango on demand
    html = render_invoice_html(invoice)
    return HTML(string=html, base_url='https://ai.checkfunnels.com').write_pdf()


def render_invoice_email(invoice, pdf_url: str = '', view_html_url: str = '',
                         conversations_url: str = '') -> str:
    """Render the SHORT transactional email body (the shell).

    This is NOT the invoice document — the document is attached as a PDF.
    The shell is the email customers actually open: subject, hero amount,
    three CTA buttons, quick stats, signoff. Keeps the email scannable
    and lets Gmail/Outlook clip nothing important.
    """
    brand_color = _safe_brand_color(invoice.brand_color_at_issue)
    brand_color_secondary = _lighten_hex(brand_color, 0.18)
    return render_to_string('billing/invoice_email.html', {
        'invoice': invoice,
        'tenant_name': invoice.company_name_at_issue,
        'company_brand': 'Checkfunnel',
        'support_email': 'support@checkfunnels.com',
        'brand_color': brand_color,
        'brand_color_secondary': brand_color_secondary,
        'brand_logo_url': (invoice.brand_logo_url_at_issue or '').strip(),
        'pdf_url': pdf_url,
        'view_html_url': view_html_url,
        'conversations_url': conversations_url,
        'usage': invoice.usage_summary or {},
    })


def email_invoice(invoice, to_email: str | None = None,
                  pdf_url: str = '', view_html_url: str = '',
                  conversations_url: str = '') -> bool:
    """
    Email the invoice — short HTML shell + the PDF as a real attachment.

    Behaviour:
      • Renders the PDF and attaches it (`Invoice <number>.pdf`).
      • Sends an HTML email with the three CTAs (Download PDF / View
        Online / View Monthly Conversations) and a quick-stats block.
      • If PDF generation fails (e.g. Pango not installed on a misconfigured
        host), we still send the email shell so the customer at least
        gets the View Online + Conversations links.

    `pdf_url` / `view_html_url` / `conversations_url` should be absolute
    URLs (signed where appropriate) — callers (Celery task / portal test
    button) build them and pass in. The template just renders them.
    """
    recipient = to_email or invoice.recipient_email_at_issue
    if not recipient:
        logger.warning(f'[invoice] No recipient for {invoice.invoice_number}')
        return False

    shell_html = render_invoice_email(
        invoice,
        pdf_url=pdf_url,
        view_html_url=view_html_url,
        conversations_url=conversations_url,
    )
    subject = (
        f'Invoice {invoice.invoice_number} · '
        f'{invoice.period_start.strftime("%B %Y")} · ${invoice.total_usd}'
    )
    plain = (
        f'Hi {invoice.company_name_at_issue},\n\n'
        f'Your Checkfunnel invoice for {invoice.period_start.strftime("%B %Y")} is ready.\n\n'
        f'Invoice number: {invoice.invoice_number}\n'
        f'Period: {invoice.period_start} to {invoice.period_end}\n'
        f'Total: ${invoice.total_usd}\n\n'
        + (f'Download PDF:\n{pdf_url}\n\n' if pdf_url else '')
        + (f'View online:\n{view_html_url}\n\n' if view_html_url else '')
        + (f'View this month\'s conversations:\n{conversations_url}\n\n' if conversations_url else '')
        + '— Checkfunnel'
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(shell_html, 'text/html')

        # Best-effort PDF attachment. If WeasyPrint isn't installed on a
        # misconfigured host, log and continue — the email still has the
        # View Online link so the customer isn't blocked.
        try:
            pdf_bytes = render_invoice_pdf(invoice)
            msg.attach(
                f'Invoice-{invoice.invoice_number}.pdf',
                pdf_bytes,
                'application/pdf',
            )
        except Exception as pdf_exc:
            logger.warning(
                f'[invoice] PDF generation failed for {invoice.invoice_number}: {pdf_exc}'
            )

        msg.send(fail_silently=False)

        invoice.status = 'sent'
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=['status', 'sent_at'])
        logger.info(f'[invoice] Sent {invoice.invoice_number} to {recipient}')
        return True
    except Exception as e:
        logger.exception(f'[invoice] Send failed for {invoice.invoice_number}: {e}')
        return False

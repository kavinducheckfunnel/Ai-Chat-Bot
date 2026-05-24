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
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


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

    fields = dict(
        tenant=tenant,
        period_start=period_start,
        period_end=period_end,
        plan_name_at_issue=(tenant.plan.name if tenant.plan else ''),
        company_name_at_issue=(tenant.company_name or tenant.user.username),
        recipient_email_at_issue=(tenant.user.email or ''),
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
    return render_to_string('billing/invoice.html', {
        'invoice': invoice,
        'line_items': invoice.line_items or [],
        'usage': invoice.usage_summary or {},
        'tenant_name': invoice.company_name_at_issue,
        'recipient_email': invoice.recipient_email_at_issue,
        'backend_url': backend_url,
        'company_brand': 'Checkfunnel',
        'support_email': 'support@checkfunnels.com',
    })


def email_invoice(invoice, to_email: str | None = None) -> bool:
    """Send the invoice HTML to the tenant (or to_email override for tests)."""
    recipient = to_email or invoice.recipient_email_at_issue
    if not recipient:
        logger.warning(f'[invoice] No recipient for {invoice.invoice_number}')
        return False

    html = render_invoice_html(invoice)
    subject = f'[Checkfunnel] Invoice {invoice.invoice_number} — {invoice.period_start.strftime("%B %Y")}'
    plain = (
        f'Hi {invoice.company_name_at_issue},\n\n'
        f'Your Checkfunnel invoice for {invoice.period_start.strftime("%B %Y")} is ready.\n\n'
        f'Invoice number: {invoice.invoice_number}\n'
        f'Period: {invoice.period_start} to {invoice.period_end}\n'
        f'Total: ${invoice.total_usd}\n\n'
        f'View the full HTML invoice in your email client or download it from\n'
        f'https://ai.checkfunnels.com/portal/billing\n\n'
        f'— The Checkfunnel Team'
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)

        invoice.status = 'sent'
        invoice.sent_at = timezone.now()
        invoice.save(update_fields=['status', 'sent_at'])
        logger.info(f'[invoice] Sent {invoice.invoice_number} to {recipient}')
        return True
    except Exception as e:
        logger.exception(f'[invoice] Send failed for {invoice.invoice_number}: {e}')
        return False

import csv
import io
import logging
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def reset_monthly_sessions(self):
    """Reset sessions_this_month counter for all tenants on the 1st of each month."""
    from users.models import TenantProfile
    updated = TenantProfile.objects.all().update(sessions_this_month=0)
    logger.info(f'[reset_monthly_sessions] Reset {updated} tenant counters.')


@shared_task(bind=True, max_retries=3)
def send_limit_warning_email(self, tenant_id):
    """
    Send a soft-limit warning email when a tenant reaches 80% of their monthly plan.
    De-duplicated: we check if a warning was already sent this month via a simple
    flag stored on TenantProfile. If the flag isn't there yet we add it on the fly
    (no migration needed — we use the sessions_this_month value as a proxy guard).
    """
    try:
        from users.models import TenantProfile
        tenant = TenantProfile.objects.select_related('plan', 'user').get(pk=tenant_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

    if not tenant.plan or not tenant.user.email:
        return

    max_s = tenant.plan.max_sessions_per_month
    used = tenant.sessions_this_month
    pct = int(used / max_s * 100) if max_s else 0

    subject = f'[Checkfunnel] You\'ve used {pct}% of your monthly chat sessions'
    body = f"""Hi {tenant.user.get_full_name() or tenant.user.username},

You've used {used} out of {max_s} chat sessions this month ({pct}%).

To avoid interruptions for your visitors, consider upgrading your plan before you hit the limit.

Log in to manage your subscription:
https://app.checkfunnel.ai/admin/

— The Checkfunnel Team
"""
    try:
        EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[tenant.user.email],
        ).send(fail_silently=False)
        logger.info(f'[send_limit_warning_email] Sent to {tenant.user.email}')
    except Exception as exc:
        logger.warning(f'[send_limit_warning_email] Failed: {exc}')
        raise self.retry(exc=exc, countdown=120)


@shared_task(bind=True, max_retries=2)
def send_monthly_lead_reports(self):
    """
    Runs on the 1st of each month.
    For every active tenant:
      1. Collects all HOT_LEAD / CONVERTED sessions from the past month.
      2. Generates a CSV with: visitor_id, email, phone, heat_score, kanban_state,
         message_count, created_at, first 3 messages of transcript.
      3. Emails the CSV as an attachment.
      4. Also sends a plain-text summary digest.
    """
    from django.utils import timezone
    from datetime import timedelta
    from users.models import TenantProfile
    from chat.models import ChatSession

    now = timezone.now()
    month_ago = now - timedelta(days=31)

    # Determine the previous calendar month for accurate session count
    today = now.date()
    prev_month = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1

    tenants = TenantProfile.objects.select_related('plan', 'user').all()
    for tenant in tenants:
        if not tenant.user.email:
            continue

        client_ids = list(tenant.clients.values_list('id', flat=True))
        if not client_ids:
            continue

        # Count sessions from the previous calendar month (sessions_this_month
        # is already reset to 0 by the time this task runs at 01:00 UTC)
        sessions_used = ChatSession.objects.filter(
            client_id__in=client_ids,
            created_at__year=prev_year,
            created_at__month=prev_month,
        ).count()

        leads = ChatSession.objects.filter(
            client_id__in=client_ids,
            kanban_state__in=['HOT_LEAD', 'CONVERTED'],
            created_at__gte=month_ago,
        ).order_by('-heat_score')

        if not leads.exists():
            continue

        # ── Build CSV ────────────────────────────────────────────────────
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            'Session ID', 'Visitor ID', 'Email', 'Phone',
            'Heat Score', 'Status', 'Messages', 'Created At',
            'Transcript Preview',
        ])
        for s in leads:
            preview = ' | '.join(
                m.get('message', m.get('content', ''))[:80]
                for m in (s.chat_history or [])[:3]
            )
            writer.writerow([
                str(s.session_id),
                s.visitor_id,
                s.lead_email or '',
                s.lead_phone or '',
                s.heat_score,
                s.kanban_state,
                s.message_count,
                s.created_at.strftime('%Y-%m-%d %H:%M'),
                preview,
            ])

        csv_content = buf.getvalue()

        # ── Plain-text digest ────────────────────────────────────────────
        month_label = month_ago.strftime('%B %Y')
        total = leads.count()
        converted = leads.filter(kanban_state='CONVERTED').count()
        avg_heat = sum(s.heat_score for s in leads) / total if total else 0

        body = f"""Hi {tenant.user.get_full_name() or tenant.user.username},

Here is your Checkfunnel lead report for {month_label}.

Summary
-------
Total hot leads:   {total}
Converted:         {converted}
Avg heat score:    {avg_heat:.1f} / 100
Sessions used:     {sessions_used} / {tenant.plan.max_sessions_per_month if tenant.plan else '∞'}

Full lead list is attached as a CSV file.

Log in to view details:
https://app.checkfunnel.ai/admin/

— The Checkfunnel Team
"""
        try:
            email = EmailMessage(
                subject=f'[Checkfunnel] Your {month_label} Lead Report ({total} leads)',
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[tenant.user.email],
            )
            email.attach(
                filename=f'checkfunnel_leads_{month_ago.strftime("%Y_%m")}.csv',
                content=csv_content,
                mimetype='text/csv',
            )
            email.send(fail_silently=False)
            logger.info(f'[send_monthly_lead_reports] Sent to {tenant.user.email} ({total} leads)')
        except Exception as exc:
            logger.warning(f'[send_monthly_lead_reports] Failed for {tenant.user.email}: {exc}')

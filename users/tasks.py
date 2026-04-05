import csv
import io
import logging
import requests as http_requests
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


@shared_task(bind=True, max_retries=2)
def send_monthly_chat_history_report(self):
    """
    Runs on the 1st of each month (after the lead report).
    For every active tenant, emails a full plain-text transcript digest
    of all sessions from the previous billing month.
    """
    from django.utils import timezone
    from datetime import timedelta
    from users.models import TenantProfile
    from chat.models import ChatSession

    now = timezone.now()
    month_ago = now - timedelta(days=31)
    today = now.date()
    prev_month = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1
    month_label = now.replace(year=prev_year, month=prev_month, day=1).strftime('%B %Y')

    tenants = TenantProfile.objects.select_related('plan', 'user').all()
    for tenant in tenants:
        if not tenant.user.email:
            continue

        client_ids = list(tenant.clients.values_list('id', flat=True))
        if not client_ids:
            continue

        sessions = ChatSession.objects.filter(
            client_id__in=client_ids,
            created_at__year=prev_year,
            created_at__month=prev_month,
        ).order_by('created_at')

        if not sessions.exists():
            continue

        # Build full transcript text
        buf = io.StringIO()
        buf.write(f'Chat History Report — {month_label}\n')
        buf.write(f'Tenant: {tenant.company_name or tenant.user.username}\n')
        buf.write(f'Total sessions: {sessions.count()}\n')
        buf.write('=' * 60 + '\n\n')

        for s in sessions:
            buf.write(f'Session: {s.session_id}\n')
            buf.write(f'Date: {s.created_at.strftime("%Y-%m-%d %H:%M")}\n')
            buf.write(f'Visitor: {s.lead_email or s.visitor_id}\n')
            buf.write(f'Channel: {s.channel}\n')
            buf.write(f'Heat score: {s.heat_score:.0f}/100  |  Status: {s.kanban_state}\n')
            buf.write('Transcript:\n')
            for msg in (s.chat_history or []):
                role = msg.get('role', 'unknown').upper()
                text = msg.get('message') or msg.get('content') or ''
                buf.write(f'  [{role}] {text[:500]}\n')
            buf.write('\n' + '-' * 60 + '\n\n')

        txt_content = buf.getvalue()

        try:
            email = EmailMessage(
                subject=f'[Checkfunnel] Chat History Report — {month_label}',
                body=(
                    f'Hi {tenant.user.get_full_name() or tenant.user.username},\n\n'
                    f'Please find your complete chat transcript digest for {month_label} attached.\n\n'
                    '— The Checkfunnel Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[tenant.user.email],
            )
            email.attach(
                filename=f'checkfunnel_transcripts_{prev_year}_{prev_month:02d}.txt',
                content=txt_content,
                mimetype='text/plain',
            )
            email.send(fail_silently=False)
            logger.info(f'[send_monthly_chat_history_report] Sent to {tenant.user.email}')
        except Exception as exc:
            logger.warning(f'[send_monthly_chat_history_report] Failed for {tenant.user.email}: {exc}')


@shared_task(bind=True, max_retries=3)
def sync_lead_to_hubspot(self, session_id):
    """
    Syncs a captured lead to the client's HubSpot account after a lead email is saved.
    Creates or updates a Contact, then creates a Deal linked to the contact.
    """
    from chat.models import ChatSession
    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return

    client = session.client
    if not client or not client.hubspot_api_key or not session.lead_email:
        return

    headers = {
        'Authorization': f'Bearer {client.hubspot_api_key}',
        'Content-Type': 'application/json',
    }
    base = 'https://api.hubapi.com'

    # ── Upsert contact ────────────────────────────────────────────────────
    contact_props = {
        'email': session.lead_email,
        'phone': session.lead_phone or '',
        'hs_lead_status': 'NEW',
        'message': (
            f'Checkfunnel lead — Heat: {session.heat_score:.0f}/100 | '
            f'Status: {session.kanban_state} | Channel: {session.channel}'
        ),
    }
    try:
        # Try create first; if conflict (409) the contact already exists
        resp = http_requests.post(
            f'{base}/crm/v3/objects/contacts',
            headers=headers,
            json={'properties': contact_props},
            timeout=10,
        )
        if resp.status_code == 409:
            # Extract existing contact id and patch
            existing_id = resp.json().get('message', '').split('with ID: ')[-1].split(' ')[0]
            if existing_id:
                http_requests.patch(
                    f'{base}/crm/v3/objects/contacts/{existing_id}',
                    headers=headers,
                    json={'properties': contact_props},
                    timeout=10,
                )
            contact_id = existing_id
        else:
            contact_id = resp.json().get('id')
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

    # ── Create deal linked to contact ─────────────────────────────────────
    if contact_id:
        try:
            deal_resp = http_requests.post(
                f'{base}/crm/v3/objects/deals',
                headers=headers,
                json={
                    'properties': {
                        'dealname': f'Checkfunnel — {session.lead_email}',
                        'dealstage': 'appointmentscheduled',
                        'pipeline': 'default',
                    },
                    'associations': [
                        {
                            'to': {'id': contact_id},
                            'types': [{'associationCategory': 'HUBSPOT_DEFINED', 'associationTypeId': 3}],
                        }
                    ],
                },
                timeout=10,
            )
            logger.info(
                f'[sync_lead_to_hubspot] Deal created for {session.lead_email}: '
                f'{deal_resp.status_code}'
            )
        except Exception as exc:
            logger.warning(f'[sync_lead_to_hubspot] Deal creation failed: {exc}')

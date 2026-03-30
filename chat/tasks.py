import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1)
def schedule_afk_nudge(self, session_id):
    """
    Fires 2 minutes after being scheduled.
    If the visitor hasn't sent a message since the task was queued,
    we inject an AFK nudge message into their WebSocket.
    """
    from chat.models import ChatSession
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return

    # Skip if already sent or if visitor has been active in last 1 min
    if session.afk_nudge_sent or session.takeover_active:
        return

    cutoff = timezone.now() - timedelta(minutes=1)
    if session.last_visitor_message_at and session.last_visitor_message_at > cutoff:
        return  # Visitor is still active

    # Build nudge message based on client config
    client = session.client
    nudge_message = "Still exploring? I can help you decide. What's holding you back?"
    if client and client.cta_message:
        nudge_message = client.cta_message
    if client and client.discount_code and session.closing_triggered:
        nudge_message = (
            f"{client.cta_message or 'Ready to take the next step?'} "
            f"Use code **{client.discount_code}** for an exclusive discount!"
        )

    # Append to chat history
    history = session.chat_history or []
    history.append({'role': 'ai', 'message': nudge_message, 'source': 'afk_nudge'})
    session.chat_history = history
    session.afk_nudge_sent = True
    session.save(update_fields=['chat_history', 'afk_nudge_sent'])

    # Push to visitor's WebSocket
    channel_layer = get_channel_layer()
    group_name = f'chat_{session_id}'
    async_to_sync(channel_layer.group_send)(group_name, {
        'type': 'chat_message',
        'message': nudge_message,
        'source': 'afk_nudge',
    })


# Nudge messages rotate to avoid repetition across multiple fires
_NUDGE_MESSAGES = [
    "Still there? I'm here to help if you have any questions!",
    "Just checking in — can I help you find what you're looking for?",
    "Take your time! Let me know if you'd like a recommendation.",
]


@shared_task
def check_afk_sessions():
    """
    Periodic task (every 2 min): find sessions idle for 2+ minutes.
    Fires up to 3 nudges per session with a minimum 5-minute gap between nudges.
    Uses nudge_count and last_nudge_at to track multi-fire state.
    """
    from chat.models import ChatSession
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from django.db import models as db_models

    now = timezone.now()
    idle_cutoff = now - timedelta(minutes=2)       # must be idle 2+ min
    nudge_gap_cutoff = now - timedelta(minutes=5)  # min 5 min between nudges

    idle_sessions = ChatSession.objects.filter(
        takeover_active=False,
        last_visitor_message_at__isnull=False,
        last_visitor_message_at__lte=idle_cutoff,
        message_count__gte=1,
        nudge_count__lt=3,  # max 3 nudges per session
    ).filter(
        # Either never nudged, or last nudge was 5+ min ago
        db_models.Q(last_nudge_at__isnull=True) | db_models.Q(last_nudge_at__lte=nudge_gap_cutoff)
    ).select_related('client')

    channel_layer = get_channel_layer()
    fired = 0
    for session in idle_sessions:
        client = session.client
        nudge_index = session.nudge_count % len(_NUDGE_MESSAGES)
        nudge_message = _NUDGE_MESSAGES[nudge_index]

        # Override with client-specific message if configured
        if client and client.discount_code and session.closing_triggered:
            nudge_message = (
                f"{client.cta_message or 'Ready to take the next step?'} "
                f"Use code **{client.discount_code}** for an exclusive discount!"
            )
        elif client and client.cta_message:
            nudge_message = client.cta_message

        history = session.chat_history or []
        history.append({'role': 'ai', 'message': nudge_message, 'source': 'afk_nudge'})
        new_count = session.nudge_count + 1
        ChatSession.objects.filter(session_id=session.session_id).update(
            chat_history=history,
            nudge_count=new_count,
            last_nudge_at=now,
            # Mark afk_nudge_sent only after all 3 nudges are exhausted
            afk_nudge_sent=(new_count >= 3),
        )
        group_name = f'chat_{session.session_id}'
        try:
            async_to_sync(channel_layer.group_send)(group_name, {
                'type': 'chat_message',
                'message': nudge_message,
                'source': 'afk_nudge',
            })
            fired += 1
        except Exception:
            pass

    import logging
    logging.getLogger(__name__).info(f'[check_afk_sessions] Fired nudge for {fired} sessions.')


@shared_task
def trigger_fomo_for_hot_sessions():
    """
    Periodic task: find hot sessions (heat >= 75) that haven't triggered FOMO yet
    and fire the closing CTA.
    """
    from chat.models import ChatSession
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    hot = ChatSession.objects.filter(heat_score__gte=75, closing_triggered=False)
    channel_layer = get_channel_layer()

    for session in hot:
        client = session.client
        fomo_text = None
        if client and client.fomo_offer_text:
            fomo_text = client.fomo_offer_text
        elif client and client.discount_code:
            fomo_text = (
                f"Limited time offer! Use code **{client.discount_code}** "
                f"before it expires."
            )

        if fomo_text:
            history = session.chat_history or []
            history.append({'role': 'ai', 'message': fomo_text, 'source': 'fomo'})
            session.chat_history = history
            session.closing_triggered = True
            session.save(update_fields=['chat_history', 'closing_triggered'])

            group_name = f'chat_{session.session_id}'
            async_to_sync(channel_layer.group_send)(group_name, {
                'type': 'chat_message',
                'message': fomo_text,
                'source': 'fomo',
            })

            # C1 — fire hot lead alert email (one-time)
            if not session.hot_lead_email_sent:
                send_hot_lead_alert.delay(str(session.session_id))


# ── C1: Hot Lead Alert ────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def send_hot_lead_alert(self, session_id):
    """
    C1: Email the tenant admin when a session first crosses heat_score >= 75.
    Guarded by hot_lead_email_sent flag — fires at most once per session.
    """
    from chat.models import ChatSession
    from users.models import TenantProfile
    from django.core.mail import EmailMessage
    from django.conf import settings

    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return

    if session.hot_lead_email_sent:
        return

    tenant = TenantProfile.objects.filter(
        clients=session.client
    ).select_related('user').first()

    # Resolve recipient: client-level email takes priority over tenant account email
    recipient = (
        (session.client.notification_email if session.client else None)
        or (tenant.user.email if tenant else None)
    )
    if not recipient:
        logger.warning(f'[send_hot_lead_alert] No recipient email for session {session_id}')
        return

    client_name = session.client.name if session.client else 'Unknown'
    god_view_url = f'https://app.checkfunnel.ai/admin/godview/{session_id}'

    last_msg = ''
    for msg in reversed(session.chat_history or []):
        if msg.get('role') == 'user':
            last_msg = msg.get('message', msg.get('content', ''))[:200]
            break

    contact_lines = ''
    if session.lead_email:
        contact_lines += f'Email:       {session.lead_email}\n'
    if session.lead_phone:
        contact_lines += f'Phone:       {session.lead_phone}\n'

    subject = f'[Checkfunnel] Hot Lead on {client_name} — Heat Score {session.heat_score:.0f}/100'
    body = (
        f'A visitor on {client_name} just reached a heat score of '
        f'{session.heat_score:.1f}/100 — they\'re showing strong buying intent.\n\n'
        f'Visitor:     {session.visitor_id}\n'
        f'Stage:       {session.kanban_state}\n'
        f'Heat Score:  {session.heat_score:.1f} / 100\n'
        f'{contact_lines}\n'
        f'Last message:\n"{last_msg}"\n\n'
        f'View live session:\n{god_view_url}\n\n'
        f'— The Checkfunnel Team\n'
    )

    try:
        EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        ).send(fail_silently=False)
        ChatSession.objects.filter(session_id=session_id).update(hot_lead_email_sent=True)
        logger.info(f'[send_hot_lead_alert] Sent to {recipient} for session {session_id}')
    except Exception as exc:
        logger.warning(f'[send_hot_lead_alert] Failed: {exc}')
        raise self.retry(exc=exc, countdown=60)


# ── C3: Takeover Request Alert ────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def send_takeover_alert(self, session_id):
    """
    C3: Email the tenant admin when a visitor asks to speak to a human.
    Triggered from consumers.py on keyword detection.
    """
    from chat.models import ChatSession
    from users.models import TenantProfile
    from django.core.mail import EmailMessage
    from django.conf import settings

    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return

    tenant = TenantProfile.objects.filter(
        clients=session.client
    ).select_related('user').first()

    # Resolve recipient: client-level email takes priority over tenant account email
    recipient = (
        (session.client.notification_email if session.client else None)
        or (tenant.user.email if tenant else None)
    )
    if not recipient:
        logger.warning(f'[send_takeover_alert] No recipient email for session {session_id}')
        return

    client_name = session.client.name if session.client else 'Unknown'
    god_view_url = f'https://app.checkfunnel.ai/admin/godview/{session_id}'

    last_msg = ''
    for msg in reversed(session.chat_history or []):
        if msg.get('role') == 'user':
            last_msg = msg.get('message', msg.get('content', ''))[:200]
            break

    contact_lines = ''
    if session.lead_email:
        contact_lines += f'Email:       {session.lead_email}\n'

    subject = f'[Checkfunnel] Visitor requesting human support on {client_name}'
    body = (
        f'A visitor on {client_name} is asking to speak to a human agent.\n\n'
        f'Visitor:     {session.visitor_id}\n'
        f'Heat Score:  {session.heat_score:.1f} / 100\n'
        f'Stage:       {session.kanban_state}\n'
        f'{contact_lines}\n'
        f'Last message:\n"{last_msg}"\n\n'
        f'Take over this session now:\n{god_view_url}\n\n'
        f'— The Checkfunnel Team\n'
    )

    try:
        EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        ).send(fail_silently=False)
        logger.info(f'[send_takeover_alert] Sent to {recipient} for session {session_id}')
    except Exception as exc:
        logger.warning(f'[send_takeover_alert] Failed: {exc}')
        raise self.retry(exc=exc, countdown=60)


# ── C2: Daily Digest ──────────────────────────────────────────────────────────

@shared_task
def send_daily_digest():
    """
    C2: Daily email per tenant at 08:00 UTC.
    Summarises today's sessions, leads captured, and top sessions by heat score.
    Skipped for tenants with no activity today.
    """
    from django.db import models as db_models
    from users.models import TenantProfile
    from chat.models import ChatSession
    from django.core.mail import EmailMessage
    from django.conf import settings

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    date_label = today_start.strftime('%B %d, %Y')

    tenants = TenantProfile.objects.select_related('user').all()
    for tenant in tenants:
        if not tenant.user.email:
            continue

        client_ids = list(tenant.clients.values_list('id', flat=True))
        if not client_ids:
            continue

        sessions_today = ChatSession.objects.filter(
            client_id__in=client_ids,
            created_at__gte=today_start,
        )
        total = sessions_today.count()
        if total == 0:
            continue  # Nothing to report

        has_contact = (
            db_models.Q(lead_email__isnull=False) & ~db_models.Q(lead_email='')
        ) | (
            db_models.Q(lead_phone__isnull=False) & ~db_models.Q(lead_phone='')
        )
        leads_count = sessions_today.filter(has_contact).count()

        avg_heat = sessions_today.aggregate(
            avg=db_models.Avg('heat_score')
        )['avg'] or 0.0

        top_sessions = list(sessions_today.order_by('-heat_score')[:3])
        top_lines = ''
        for i, s in enumerate(top_sessions, 1):
            top_lines += (
                f'  {i}. Heat {s.heat_score:.0f}/100'
                f' — {s.visitor_id} ({s.kanban_state})\n'
            )

        subject = f'[Checkfunnel] Daily Digest — {date_label}'
        body = (
            f'Hi {tenant.user.get_full_name() or tenant.user.username},\n\n'
            f"Here's your Checkfunnel activity summary for {date_label}.\n\n"
            f'Today\'s Stats\n'
            f'-------------\n'
            f'Sessions started:    {total}\n'
            f'Leads captured:      {leads_count}\n'
            f'Avg heat score:      {avg_heat:.1f} / 100\n\n'
            f'Top Sessions by Heat Score\n'
            f'--------------------------\n'
            f'{top_lines or "  No sessions yet."}\n'
            f'Log in to your dashboard:\n'
            f'https://app.checkfunnel.ai/admin/\n\n'
            f'— The Checkfunnel Team\n'
        )

        try:
            EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[tenant.user.email],
            ).send(fail_silently=False)
            logger.info(f'[send_daily_digest] Sent to {tenant.user.email}')
        except Exception as exc:
            logger.warning(f'[send_daily_digest] Failed for {tenant.user.email}: {exc}')


@shared_task
def archive_long_sessions():
    """
    Daily safety net: find any ChatSession where chat_history has grown beyond
    200 entries (e.g. via admin takeover or direct DB writes) and truncate them.
    Uses PostgreSQL jsonb_array_length for an efficient server-side filter.
    """
    from django.db.models import Func, IntegerField
    from .models import ChatSession
    from .utils import truncate_chat_history

    oversized = ChatSession.objects.annotate(
        history_len=Func(
            'chat_history',
            function='jsonb_array_length',
            output_field=IntegerField(),
        )
    ).filter(history_len__gt=200)

    count = 0
    for session in oversized:
        fields = truncate_chat_history(session)
        session.save(update_fields=fields)
        count += 1

    logger.info(f'[archive_long_sessions] Truncated {count} session(s).')

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

    # ── Respect cta_mode — tenant chose one CTA strategy ─────────────────
    client = session.client
    cta_mode = getattr(client, 'cta_mode', 'ai') if client else 'ai'
    if cta_mode == 'off':
        return  # tenant turned off automated follow-ups entirely

    nudge_message = _build_nudge_message(session, client, cta_mode)
    if not nudge_message:
        return  # AI generation failed and no manual text → skip silently

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


# Generic fallback rotation — ONLY used when there's no client/browsing
# context to personalise against. Even these are written to nudge the
# visitor back toward a qualifying decision instead of being filler.
_GENERIC_NUDGE_MESSAGES = [
    "Still browsing? I can recommend something quick — what's caught your eye?",
    "Want me to narrow it down for you? Just tell me size / budget / use-case.",
    "Quick question — looking to buy soon, or still researching?",
]

# Context-aware nudge templates. {top_interest} gets replaced with the
# visitor's most-dwelled product/page. The QA report flagged generic
# "Still there?" / "Just checking in" as 2.5/10 — these address that by
# referencing what the visitor was ACTUALLY looking at.
_PERSONALISED_NUDGE_TEMPLATES = [
    "Still thinking about {top_interest}? Happy to answer any quick questions.",
    "Want me to check size / availability on {top_interest}?",
    "Saw you were looking at {top_interest} — what would help you decide?",
]


def _build_nudge_message(session, client, cta_mode):
    """
    Build the text for an AFK follow-up nudge based on the tenant's chosen
    CTA strategy. Returns None if no message should be sent.

    cta_mode='ai'     → ask the LLM to write a personalised CTA referencing
                        the visitor's browsing context + EMA signals. Falls
                        back to a context-aware template if the LLM fails,
                        and finally to a generic line.
    cta_mode='manual' → use client.cta_message verbatim. If the tenant left
                        cta_message blank, send nothing (we don't want to
                        accidentally fall back to AI text).
    cta_mode='off'    → caller already returned earlier.
    """
    if cta_mode == 'manual':
        text = (client.cta_message or '').strip() if client else ''
        return text or None  # don't fire on empty manual text

    # AI mode — try the personaliser first.
    try:
        from chat.views import _generate_personalised_cta
        personalised = _generate_personalised_cta(session, client, 'afk_nudge')
        if personalised:
            return personalised
    except Exception as e:
        logger.warning(f'[_build_nudge_message] AI generation failed: {e}')

    # Context-aware fallback — pull the visitor's top_interest if any.
    nudge_count = getattr(session, 'nudge_count', 0) or 0
    top_interest = ''
    try:
        from chat.ai_service import build_browsing_context
        bs = build_browsing_context(session) or {}
        top_interest = (bs.get('top_interest') or '').strip()
    except Exception:
        pass

    if top_interest:
        template = _PERSONALISED_NUDGE_TEMPLATES[nudge_count % len(_PERSONALISED_NUDGE_TEMPLATES)]
        return template.format(top_interest=top_interest)

    # No context at all — use the qualification-leaning generics.
    return _GENERIC_NUDGE_MESSAGES[nudge_count % len(_GENERIC_NUDGE_MESSAGES)]


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
        afk_nudge_sent=False,  # skip if one-shot nudge already fired
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
        cta_mode = getattr(client, 'cta_mode', 'ai') if client else 'ai'
        if cta_mode == 'off':
            continue  # tenant disabled automated follow-ups

        nudge_message = _build_nudge_message(session, client, cta_mode)
        if not nudge_message:
            continue  # manual mode with empty cta_message → skip silently

        history = session.chat_history or []
        history.append({'role': 'ai', 'message': nudge_message, 'source': 'afk_nudge'})
        new_count = session.nudge_count + 1
        # For manual CTA, one nudge is enough — identical repeat messages feel like spam
        is_done = (new_count >= 3) or (cta_mode == 'manual')
        ChatSession.objects.filter(session_id=session.session_id).update(
            chat_history=history,
            nudge_count=new_count,
            last_nudge_at=now,
            afk_nudge_sent=is_done,
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

    # ── Slack notification ────────────────────────────────────────────────────
    if session.client:
        from chat.utils import fire_slack_notification, fire_outbound_webhook
        slack_text = (
            f':fire: *Hot Lead on {client_name}* — Heat {session.heat_score:.0f}/100\n'
            f'Visitor: {session.visitor_id}'
            + (f' · {session.lead_email}' if session.lead_email else '')
            + f'\n<{god_view_url}|View live session>'
        )
        fire_slack_notification(session.client, slack_text)
        fire_outbound_webhook(session.client, 'hot_lead', {
            'session_id': str(session.session_id),
            'visitor_id': session.visitor_id,
            'lead_email': session.lead_email or '',
            'lead_phone': session.lead_phone or '',
            'heat_score': session.heat_score,
            'kanban_state': session.kanban_state,
            'god_view_url': god_view_url,
        })


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


@shared_task
def tag_session_outcomes(batch_size=500):
    """Auto-classify ChatSession.outcome for E1 KPI tracking.

    Runs hourly via Celery beat. Looks at sessions where outcome='open'
    and applies a fixed precedence:
      1. message_count == 0 → 'ghost' (excluded from KPIs)
      2. kanban_state == 'CONVERTED' → 'converted'
      3. taken_over_by is set → 'escalated'
      4. lead_email or lead_phone present → 'captured'
      5. last_visitor_message_at older than 30 min → 'abandoned'
    Sessions that don't yet match any of the above stay 'open' so they
    don't pollute the KPI dashboard mid-conversation.
    """
    from chat.models import ChatSession
    from django.utils import timezone
    from datetime import timedelta
    from django.db import models as dj_models

    now = timezone.now()
    idle_cutoff = now - timedelta(minutes=30)

    qs = ChatSession.objects.filter(outcome='open').order_by('created_at')[:batch_size]
    tagged = {}
    for s in qs:
        if (s.message_count or 0) == 0:
            new_outcome = 'ghost'
        elif s.kanban_state == 'CONVERTED':
            new_outcome = 'converted'
        elif s.taken_over_by_id:
            new_outcome = 'escalated'
        elif (s.lead_email or s.lead_phone):
            new_outcome = 'captured'
        elif s.last_visitor_message_at and s.last_visitor_message_at < idle_cutoff:
            new_outcome = 'abandoned'
        else:
            continue  # still active — leave as 'open'

        ChatSession.objects.filter(session_id=s.session_id).update(
            outcome=new_outcome, outcome_set_at=now,
        )
        tagged[new_outcome] = tagged.get(new_outcome, 0) + 1

    if tagged:
        logger.info(f'[tag_session_outcomes] Tagged {sum(tagged.values())} sessions: {dict(tagged)}')
    return tagged

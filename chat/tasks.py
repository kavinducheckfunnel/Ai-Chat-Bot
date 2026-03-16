from celery import shared_task
from django.utils import timezone
from datetime import timedelta


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

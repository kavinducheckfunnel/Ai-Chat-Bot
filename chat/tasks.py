from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task(bind=True, max_retries=1)
def schedule_afk_nudge(self, session_id):
    """
    Fires 5 minutes after being scheduled.
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

    # Skip if already sent or if visitor has been active in last 4 min
    if session.afk_nudge_sent or session.takeover_active:
        return

    cutoff = timezone.now() - timedelta(minutes=4)
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


@shared_task
def check_afk_sessions():
    """
    Periodic task (every 5 min): find sessions idle for 5+ minutes where no
    nudge has been sent yet, and fire the AFK nudge into their WebSocket.
    """
    from chat.models import ChatSession
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    cutoff = timezone.now() - timedelta(minutes=5)
    idle_sessions = ChatSession.objects.filter(
        afk_nudge_sent=False,
        takeover_active=False,
        last_visitor_message_at__isnull=False,
        last_visitor_message_at__lte=cutoff,
        # Only sessions that have at least one message (real visitor)
        message_count__gte=1,
    ).select_related('client')

    channel_layer = get_channel_layer()
    fired = 0
    for session in idle_sessions:
        client = session.client
        nudge_message = "Still there? I'm here to help if you have any questions!"
        if client and client.discount_code and session.closing_triggered:
            nudge_message = (
                f"{client.cta_message or 'Ready to take the next step?'} "
                f"Use code **{client.discount_code}** for an exclusive discount!"
            )
        elif client and client.cta_message:
            nudge_message = client.cta_message

        history = session.chat_history or []
        history.append({'role': 'ai', 'message': nudge_message, 'source': 'afk_nudge'})
        ChatSession.objects.filter(session_id=session.session_id).update(
            chat_history=history,
            afk_nudge_sent=True,
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

from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from datetime import timedelta


@shared_task
def send_afk_nudges():
    """
    Periodic task (runs every 15s via Celery Beat).
    For each active session where:
      - heat_score > 30
      - no message in last 45 seconds
      - last nudge was > 2 minutes ago (or never)
      - takeover_active is False
    → inject a proactive re-engagement message via WebSocket.
    """
    from chat.models import ChatSession

    now = timezone.now()
    afk_cutoff = now - timedelta(seconds=45)
    nudge_cooldown = now - timedelta(minutes=2)

    candidates = ChatSession.objects.filter(
        heat_score__gt=30,
        takeover_active=False,
        updated_at__lt=afk_cutoff,
        message_count__gt=0,
    ).filter(
        # last_nudge_at is None OR last nudge > 2 min ago
        last_nudge_at__isnull=True
    ) | ChatSession.objects.filter(
        heat_score__gt=30,
        takeover_active=False,
        updated_at__lt=afk_cutoff,
        message_count__gt=0,
        last_nudge_at__lt=nudge_cooldown,
    )

    channel_layer = get_channel_layer()

    for session in candidates[:20]:  # Safety limit
        nudge_msg = _generate_nudge_message(session)

        try:
            async_to_sync(channel_layer.group_send)(
                f"chat_{session.session_id}",
                {
                    'type': 'chat_message',
                    'message': nudge_msg,
                    'sender': 'ai',
                    'is_nudge': True,
                }
            )
            session.last_nudge_at = now
            session.nudge_count += 1
            session.save(update_fields=['last_nudge_at', 'nudge_count'])
        except Exception as e:
            print(f"[AFK Nudge] Error for session {session.session_id}: {e}")


def _generate_nudge_message(session):
    """Pick a contextual nudge based on conversation state."""
    state = session.conversation_state
    last_topic = ''
    if session.chat_history:
        for msg in reversed(session.chat_history):
            if msg.get('role') == 'user':
                last_topic = msg.get('message', '')[:60]
                break

    nudges = {
        'RESEARCH': f"Still looking for the right fit? I can help narrow it down! What matters most to you?",
        'EVALUATION': "Any questions about what you were comparing? I'm here to help you decide!",
        'OBJECTION': "I know it can be a tough call — want me to walk you through the key benefits again?",
        'RECOVERY': "Still there? No pressure at all — I'm happy to help whenever you're ready.",
        'READY_TO_BUY': "Ready to get started? I can walk you through the next steps right now!",
    }
    return nudges.get(state, "Hey, still there? Let me know if you have any questions!")

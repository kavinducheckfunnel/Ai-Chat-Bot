from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def calculate_ema(current_score, previous_ema, weight_current=0.8):
    """
    Calculates the Exponential Moving Average using the 80/20 rule.
    New EMA = (Current Raw Score * 0.8) + (Previous EMA * 0.2)
    """
    return (current_score * weight_current) + (previous_ema * (1 - weight_current))


def determine_trend(current_ema, previous_ema, threshold=0.02):
    """
    Determines the trend (UP, DOWN, FLAT) based on EMA change.
    """
    diff = current_ema - previous_ema
    if diff > threshold:
        return 'UP'
    elif diff < -threshold:
        return 'DOWN'
    else:
        return 'FLAT'


def compute_heat_score(intent_ema, budget_ema, urgency_ema):
    """
    heat_score = weighted combination of EMA scores, scaled 0–100.
    Intent carries the most weight (50%), budget 30%, urgency 20%.
    """
    raw = (intent_ema * 0.5) + (budget_ema * 0.3) + (urgency_ema * 0.2)
    return round(raw * 100, 1)


def update_session_scores(session, raw_intent, raw_budget, raw_urgency):
    """
    Updates the session with new EMAs, trends, and heat score.
    Fires closing trigger if heat_score crosses 75 for the first time.
    Broadcasts a live update to the admin dashboard channel group.
    """
    # Shift current to previous
    session.previous_intent_ema = session.current_intent_ema
    session.previous_budget_ema = session.current_budget_ema
    session.previous_urgency_ema = session.current_urgency_ema

    # Calculate new EMAs
    session.current_intent_ema = calculate_ema(raw_intent, session.previous_intent_ema)
    session.current_budget_ema = calculate_ema(raw_budget, session.previous_budget_ema)
    session.current_urgency_ema = calculate_ema(raw_urgency, session.previous_urgency_ema)

    # Determine trends
    session.intent_trend = determine_trend(session.current_intent_ema, session.previous_intent_ema)
    session.budget_trend = determine_trend(session.current_budget_ema, session.previous_budget_ema)
    session.urgency_trend = determine_trend(session.current_urgency_ema, session.previous_urgency_ema)

    # Compute heat score
    session.heat_score = compute_heat_score(
        session.current_intent_ema,
        session.current_budget_ema,
        session.current_urgency_ema,
    )

    session.message_count += 1
    session.save()

    # Fire closing CTA if heat >= 75 (once per session)
    if session.heat_score >= 75 and not session.closing_triggered:
        _fire_closing_trigger(session)

    # Broadcast live update to admin dashboard
    _broadcast_session_update(session)

    return session


def _fire_closing_trigger(session):
    """Inject a closing CTA message into the visitor's chat via the session WS group."""
    try:
        client = session.client
        cta = "You're clearly ready — here's something special for you!"
        if client:
            if client.discount_code:
                cta = f"{client.cta_message or 'Special offer for you!'} **{client.discount_code}**"
            elif client.cta_message:
                cta = client.cta_message

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{session.session_id}",
            {
                "type": "chat_message",
                "message": cta,
                "sender": "ai",
                "is_trigger": True,
            }
        )
        session.closing_triggered = True
        session.save(update_fields=['closing_triggered'])
    except Exception as e:
        print(f"[EMA] Closing trigger error: {e}")


def _broadcast_session_update(session):
    """Send a live session snapshot to the admin dashboard channel group."""
    try:
        client_id = str(session.client_id) if session.client_id else None
        group_name = f"dashboard_{client_id}" if client_id else "dashboard_all"

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "session_update",
                "session_id": str(session.session_id),
                "heat_score": session.heat_score,
                "conversation_state": session.conversation_state,
                "intent_ema": round(session.current_intent_ema, 3),
                "budget_ema": round(session.current_budget_ema, 3),
                "urgency_ema": round(session.current_urgency_ema, 3),
                "message_count": session.message_count,
                "last_message_at": session.updated_at.isoformat() if session.updated_at else None,
                "visitor_id": session.visitor_id,
                "takeover_active": session.takeover_active,
                "taken_over_by": session.taken_over_by_id,
            }
        )
        # Also broadcast to "dashboard_all" group for superadmins
        if client_id:
            async_to_sync(channel_layer.group_send)(
                "dashboard_all",
                {
                    "type": "session_update",
                    "session_id": str(session.session_id),
                    "heat_score": session.heat_score,
                    "conversation_state": session.conversation_state,
                    "intent_ema": round(session.current_intent_ema, 3),
                    "budget_ema": round(session.current_budget_ema, 3),
                    "urgency_ema": round(session.current_urgency_ema, 3),
                    "message_count": session.message_count,
                    "last_message_at": session.updated_at.isoformat() if session.updated_at else None,
                    "visitor_id": session.visitor_id,
                    "takeover_active": session.takeover_active,
                    "taken_over_by": session.taken_over_by_id,
                    "client_id": client_id,
                }
            )
    except Exception as e:
        print(f"[EMA] Dashboard broadcast error: {e}")

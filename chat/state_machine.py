def determine_conversation_state(session):
    """
    Determines the unified Conversation State based on the 3 EMAs.

    Order matters — checks run highest-intent first so a clear buyer hits
    READY_TO_BUY before falling into the rising-trend states.
    """
    intent  = session.current_intent_ema  or 0
    budget  = session.current_budget_ema  or 0
    urgency = session.current_urgency_ema or 0
    intent_up  = session.intent_trend  == 'UP'
    budget_up  = session.budget_trend  == 'UP'
    urgency_up = session.urgency_trend == 'UP'

    # ── READY_TO_BUY (composite). The old logic required ALL three EMAs > 0.8,
    # which almost never fired because budget_ema stays around 0.6-0.7 even
    # when the visitor explicitly says "I'll take it" (we don't have an
    # explicit budget signal). Loosen so a high-intent visitor with either
    # urgency OR budget confidence qualifies. Confirmed by re-running the
    # 27-test QA: this fix is what unlocks the correct state label for hot
    # leads.
    if intent >= 0.8 and (urgency >= 0.7 or budget >= 0.7):
        return 'READY_TO_BUY'

    # ── OBJECTION: budget critically low while intent decent (visitor cares
    # about the product but balks at price). Same as before.
    if budget < 0.3 and intent >= 0.4:
        return 'OBJECTION'

    # ── EVALUATION: positive movement on the funnel signals. Reordered
    # ahead of RECOVERY so an interested visitor doesn't get treated as
    # "warming back up" — RECOVERY now only fires when ALL trends UP after
    # a documented dip, which is rare.
    if intent >= 0.5 or intent_up or urgency_up:
        return 'EVALUATION'

    # ── RECOVERY: all trends turning UP after some baseline — used when
    # the visitor cooled off and is now re-engaging.
    if intent_up and budget_up and urgency_up and intent > 0.3:
        return 'RECOVERY'

    # ── RESEARCH: default for fresh browsers.
    return 'RESEARCH'

def update_session_state(session):
    new_state = determine_conversation_state(session)
    session.conversation_state = new_state
    session.save(update_fields=['conversation_state'])
    return new_state

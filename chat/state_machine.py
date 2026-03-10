def determine_conversation_state(session):
    """
    Determines the unified Conversation State based on the 3 EMAs.
    Logic described in section 4.4
    """
    intent = session.current_intent_ema
    budget = session.current_budget_ema
    urgency = session.current_urgency_ema
    
    intent_up = session.intent_trend == 'UP'
    budget_up = session.budget_trend == 'UP'
    urgency_up = session.urgency_trend == 'UP'
    
    # Ready to Buy: All 3 EMAs > 0.8
    if intent > 0.8 and budget > 0.8 and urgency > 0.8:
        return 'READY_TO_BUY'
        
    # Objection Mode: Budget critically low (<0.3) while Intent decent
    if budget < 0.3 and intent >= 0.4:
        return 'OBJECTION'
        
    # Recovery Mode: All trends turning UP after a dip
    # (Simplified: if all trends UP and it's not starting from low)
    if intent_up and budget_up and urgency_up and intent > 0.4:
        return 'RECOVERY'
        
    # Evaluation Mode: Intent or Urgency rising, Budget variable
    if intent_up or urgency_up:
        return 'EVALUATION'
        
    # Research Mode: Default fallback (All EMAs low/average)
    return 'RESEARCH'

def update_session_state(session):
    new_state = determine_conversation_state(session)
    session.conversation_state = new_state
    session.save(update_fields=['conversation_state'])
    return new_state

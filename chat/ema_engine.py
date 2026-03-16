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

def update_session_scores(session, raw_intent, raw_budget, raw_urgency):
    """
    Updates the session with new EMAs and trends based on raw scores.
    """
    # Shift current to previous
    session.previous_intent_ema = session.current_intent_ema
    session.previous_budget_ema = session.current_budget_ema
    session.previous_urgency_ema = session.current_urgency_ema
    
    # Calculate new EMA
    session.current_intent_ema = calculate_ema(raw_intent, session.previous_intent_ema)
    session.current_budget_ema = calculate_ema(raw_budget, session.previous_budget_ema)
    session.current_urgency_ema = calculate_ema(raw_urgency, session.previous_urgency_ema)
    
    # Determine Trends
    session.intent_trend = determine_trend(session.current_intent_ema, session.previous_intent_ema)
    session.budget_trend = determine_trend(session.current_budget_ema, session.previous_budget_ema)
    session.urgency_trend = determine_trend(session.current_urgency_ema, session.previous_urgency_ema)
    
    session.message_count += 1
    session.save(update_fields=[
        'previous_intent_ema', 'previous_budget_ema', 'previous_urgency_ema',
        'current_intent_ema', 'current_budget_ema', 'current_urgency_ema',
        'intent_trend', 'budget_trend', 'urgency_trend',
        'message_count',
    ])
    return session

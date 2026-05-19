import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Weight used when updating EMA from behavioral signals.
# Lower than the LLM-extracted score weight (0.8) so behavioral data nudges
# rather than overrides the AI-scored values.
_BEHAVIORAL_EMA_WEIGHT = 0.3


def _apply_behavior(session, behavior):
    """
    Write behavioral signals from the beacon into a ChatSession.
    Also nudges the 3-EMA scores based on the behavioral data so that
    a visitor who browses without chatting still accumulates intent signals.
    """
    # ── Persist raw context ───────────────────────────────────────────────────
    ctx = session.behavioral_context or {}
    ctx['pages_viewed']          = len(behavior.get('pagesViewed', []))
    ctx['pricing_page_visits']   = behavior.get('pricingPageVisits', 0)
    ctx['exit_intent_triggered'] = behavior.get('exitIntentFired', False)
    ctx['scroll_depth']          = behavior.get('scrollDepth', 0)
    ctx['time_on_site']          = behavior.get('timeOnSite', 0)
    session.behavioral_context = ctx
    session.save(update_fields=['behavioral_context'])

    # ── Map behavioral signals → raw scores (0.0 – 1.0) ─────────────────────
    time_on = behavior.get('timeOnSite', 0)     # seconds
    scroll  = behavior.get('scrollDepth', 0)    # percent
    pricing = behavior.get('pricingPageVisits', 0)
    pages   = len(behavior.get('pagesViewed', []))

    # Intent: weighted blend of time-on-site (caps at 2 min) + pages viewed (caps at 8)
    raw_intent  = min((time_on / 120.0) * 0.6 + (pages / 8.0) * 0.4, 1.0)
    # Urgency: deep scroll signals active evaluation
    raw_urgency = min(scroll / 80.0, 1.0)
    # Budget: visiting pricing pages signals price consideration
    raw_budget  = min(pricing * 0.4, 1.0)

    # Only update EMA when signals cross a meaningful threshold to avoid noise
    if raw_intent < 0.08 and raw_urgency < 0.08 and raw_budget == 0.0:
        return

    try:
        from chat.ema_engine import calculate_ema, determine_trend

        prev_intent  = session.current_intent_ema
        prev_budget  = session.current_budget_ema
        prev_urgency = session.current_urgency_ema

        new_intent  = calculate_ema(raw_intent,  prev_intent,  weight_current=_BEHAVIORAL_EMA_WEIGHT)
        new_budget  = calculate_ema(raw_budget,  prev_budget,  weight_current=_BEHAVIORAL_EMA_WEIGHT)
        new_urgency = calculate_ema(raw_urgency, prev_urgency, weight_current=_BEHAVIORAL_EMA_WEIGHT)

        session.previous_intent_ema  = prev_intent
        session.previous_budget_ema  = prev_budget
        session.previous_urgency_ema = prev_urgency
        session.current_intent_ema   = new_intent
        session.current_budget_ema   = new_budget
        session.current_urgency_ema  = new_urgency
        session.intent_trend  = determine_trend(new_intent,  prev_intent)
        session.budget_trend  = determine_trend(new_budget,  prev_budget)
        session.urgency_trend = determine_trend(new_urgency, prev_urgency)

        session.save(update_fields=[
            'previous_intent_ema', 'previous_budget_ema', 'previous_urgency_ema',
            'current_intent_ema',  'current_budget_ema',  'current_urgency_ema',
            'intent_trend', 'budget_trend', 'urgency_trend',
        ])
    except Exception:
        pass  # EMA update is best-effort; behavioral context was already saved


@csrf_exempt
def beacon_receiver(request):
    """
    Receives behavioral analytics from the widget tracker (navigator.sendBeacon).
    Saves pagesViewed, pricingPageVisits, exitIntentFired, scrollDepth, timeOnSite
    into ChatSession.behavioral_context, and nudges the 3-EMA scores so that
    visitors who browse without chatting still accumulate meaningful intent signals.

    If the session doesn't exist yet (user browsed but hasn't chatted), the data
    is cached for 30 minutes and applied when the session is eventually created.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    session_id = data.get('sessionId')
    behavior = data.get('behaviorMatrix', {})

    if session_id and behavior:
        try:
            from chat.models import ChatSession
            from django.core.cache import cache

            session = ChatSession.objects.filter(session_id=session_id).first()
            if session:
                _apply_behavior(session, behavior)
            else:
                # Session not created yet — cache so the consumer can apply it on first message
                cache.set(f'beacon_{session_id}', behavior, 1800)
        except Exception:
            pass  # beacon is fire-and-forget, never block the response

    return JsonResponse({'status': 'ok'})

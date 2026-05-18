import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def _apply_behavior(session, behavior):
    """Write behavioral signals from the beacon into a ChatSession."""
    ctx = session.behavioral_context or {}
    ctx['pages_viewed']          = len(behavior.get('pagesViewed', []))
    ctx['pricing_page_visits']   = behavior.get('pricingPageVisits', 0)
    ctx['exit_intent_triggered'] = behavior.get('exitIntentFired', False)
    ctx['scroll_depth']          = behavior.get('scrollDepth', 0)
    ctx['time_on_site']          = behavior.get('timeOnSite', 0)
    session.behavioral_context = ctx
    session.save(update_fields=['behavioral_context'])


@csrf_exempt
def beacon_receiver(request):
    """
    Receives behavioral analytics from the widget tracker (navigator.sendBeacon).
    Saves pagesViewed, pricingPageVisits, exitIntentFired, scrollDepth, timeOnSite
    into ChatSession.behavioral_context.
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
                # Session not created yet — cache the data so the consumer can apply it
                cache.set(f'beacon_{session_id}', behavior, 1800)
        except Exception:
            pass  # beacon is fire-and-forget, never block the response

    return JsonResponse({'status': 'ok'})

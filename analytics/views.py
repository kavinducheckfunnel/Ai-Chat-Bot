import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def beacon_receiver(request):
    """
    Receives behavioral analytics from the widget tracker (navigator.sendBeacon).
    Saves pagesViewed, pricingPageVisits, exitIntentFired, scrollDepth, timeOnSite
    into ChatSession.behavioral_context so the admin dashboard can surface them.
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
            session = ChatSession.objects.filter(session_id=session_id).first()
            if session:
                ctx = session.behavioral_context or {}
                ctx['pages_viewed'] = len(behavior.get('pagesViewed', []))
                ctx['pricing_page_visits'] = behavior.get('pricingPageVisits', 0)
                ctx['exit_intent_triggered'] = behavior.get('exitIntentFired', False)
                ctx['scroll_depth'] = behavior.get('scrollDepth', 0)
                ctx['time_on_site'] = behavior.get('timeOnSite', 0)
                session.behavioral_context = ctx
                session.save(update_fields=['behavioral_context'])
        except Exception:
            pass  # beacon is fire-and-forget, never block the response

    return JsonResponse({'status': 'ok'})

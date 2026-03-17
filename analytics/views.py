import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from users.models import Client
from .models import AnalyticEvent


@csrf_exempt
def beacon_receiver(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid JSON'}, status=400)

    session_id = data.get('sessionId', '')
    client_id = data.get('clientId')
    events = data.get('events', [])
    behavior_matrix = data.get('behaviorMatrix', {})

    # Resolve client
    client = None
    if client_id:
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            pass

    # Persist each event
    bulk = []
    for event in events:
        event_type = event.get('type', 'beacon')
        if event_type not in dict(AnalyticEvent.EVENT_CHOICES):
            event_type = 'beacon'
        bulk.append(AnalyticEvent(
            client=client,
            session_id=session_id,
            event_type=event_type,
            page_url=event.get('url') or event.get('page', ''),
            payload=event,
        ))

    # Also persist a summary beacon record with the full behavior matrix
    if behavior_matrix and session_id:
        bulk.append(AnalyticEvent(
            client=client,
            session_id=session_id,
            event_type='beacon',
            payload={
                'behaviorMatrix': behavior_matrix,
                'eventCount': len(events),
            },
        ))

    if bulk:
        AnalyticEvent.objects.bulk_create(bulk, ignore_conflicts=True)

    return JsonResponse({'status': 'ok', 'saved': len(bulk)})


def client_analytics(request, client_id):
    """
    Returns aggregated analytics for a client — called by the admin SPA.
    """
    from django.db.models import Count
    from datetime import timedelta

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)

    now = timezone.now()
    last_30 = now - timedelta(days=30)

    events = AnalyticEvent.objects.filter(client=client, created_at__gte=last_30)

    total_page_views = events.filter(event_type='page_view').count()
    unique_sessions = events.values('session_id').distinct().count()
    pricing_visits = events.filter(event_type='pricing_visit').count()
    exit_intents = events.filter(event_type='exit_intent').count()

    # Page view breakdown by URL (top 10)
    top_pages = (
        events.filter(event_type='page_view')
        .values('page_url')
        .annotate(views=Count('id'))
        .order_by('-views')[:10]
    )

    return JsonResponse({
        'total_page_views': total_page_views,
        'unique_sessions': unique_sessions,
        'pricing_visits': pricing_visits,
        'exit_intents': exit_intents,
        'top_pages': list(top_pages),
        'period_days': 30,
    })

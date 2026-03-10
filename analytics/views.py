import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def beacon_receiver(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Could save this to analytics.models.PageView or ClickEvent
            # For Stage 1 prototype, we mainly rely on frontend keeping state.
            return JsonResponse({'status': 'ok'})
        except Exception:
            return JsonResponse({'error': 'invalid data'}, status=400)
    return JsonResponse({'error': 'method not allowed'}, status=405)

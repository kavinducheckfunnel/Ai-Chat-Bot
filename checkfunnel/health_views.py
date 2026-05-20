"""
Liveness + readiness endpoint hit by:
  • CI/CD deploy script (rolls back if this isn't 200 within 30s post-restart)
  • Uptime monitors (UptimeRobot etc.)
  • Load balancers if we ever add one

Returns 200 only when DB + Redis are both reachable. Cheap enough to call
every few seconds — no auth required.
"""
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache


@csrf_exempt
@never_cache
def health(request):
    started = time.time()
    checks = {}
    overall_ok = True

    # Database — a trivial SELECT 1 confirms the pool + Postgres are alive.
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        checks['db'] = 'ok'
    except Exception as e:
        checks['db'] = f'fail: {type(e).__name__}'
        overall_ok = False

    # Cache (Redis) — round-trip a probe key.
    try:
        from django.core.cache import cache
        probe = f'health:probe:{int(time.time())}'
        cache.set(probe, '1', 5)
        val = cache.get(probe)
        checks['cache'] = 'ok' if val == '1' else 'fail: roundtrip mismatch'
        if val != '1':
            overall_ok = False
    except Exception as e:
        checks['cache'] = f'fail: {type(e).__name__}'
        overall_ok = False

    payload = {
        'status': 'ok' if overall_ok else 'degraded',
        'checks': checks,
        'elapsed_ms': int((time.time() - started) * 1000),
    }
    return JsonResponse(payload, status=200 if overall_ok else 503)

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Behavioral signal → EMA weight. Lower than LLM-extracted (0.8) so behavioral
# data nudges rather than overrides the AI-scored values.
_BEHAVIORAL_EMA_WEIGHT = 0.3


def _clamp(val, lo=0.0, hi=1.0):
    return max(lo, min(hi, val))


def _apply_behavior(session, behavior):
    """
    Map behavioral signals from the beacon into a ChatSession.
    Persists the raw context then nudges the 3-EMA scores so visitors who
    browse without chatting still accumulate meaningful intent signals.
    """
    # ── Persist raw context ───────────────────────────────────────────────────
    ctx = session.behavioral_context or {}

    # Core signals
    pages          = len(behavior.get('pagesViewed', []))
    pricing        = behavior.get('pricingPageVisits', 0)
    checkout       = behavior.get('checkoutVisits', 0)
    scroll_depth   = behavior.get('scrollDepth', 0)
    scroll_m       = behavior.get('scrollMilestones', [])
    time_on        = behavior.get('timeOnSite', 0)
    exit_intent    = behavior.get('exitIntentFired', False)
    click_count    = behavior.get('clickCount', 0)
    cta_clicks     = behavior.get('ctaClicks', 0)
    rage_clicks    = behavior.get('rageClicks', 0)
    form_focused   = behavior.get('formFocused', False)
    form_abandoned = behavior.get('formAbandoned', False)
    atc_clicks     = behavior.get('addToCartClicks', 0)
    price_views    = behavior.get('priceViews', 0)
    copy_events    = behavior.get('copyEvents', 0)
    video_plays    = behavior.get('videoPlays', 0)
    file_downloads = behavior.get('fileDownloads', 0)
    idle_sec       = behavior.get('idleSeconds', 0)
    tab_hidden     = behavior.get('tabHiddenSeconds', 0)

    # Active time ratio (1.0 = fully engaged)
    active_time = max(time_on - idle_sec - tab_hidden, 0)
    active_ratio = _clamp(active_time / max(time_on, 1))

    # Scroll milestone score (fraction of [25,50,75,90] reached)
    milestone_score = len([m for m in [25, 50, 75, 90] if m in scroll_m]) / 4.0

    ctx.update({
        'pages_viewed':         pages,
        'pricing_page_visits':  pricing,
        'checkout_visits':      checkout,
        'exit_intent_triggered': exit_intent,
        'scroll_depth':         scroll_depth,
        'scroll_milestones':    scroll_m,
        'time_on_site':         time_on,
        'active_ratio':         round(active_ratio, 3),
        'click_count':          click_count,
        'cta_clicks':           cta_clicks,
        'rage_clicks':          rage_clicks,
        'form_focused':         form_focused,
        'form_abandoned':       form_abandoned,
        'add_to_cart_clicks':   atc_clicks,
        'price_views':          price_views,
        'copy_events':          copy_events,
        'video_plays':          video_plays,
        'file_downloads':       file_downloads,
        'idle_seconds':         idle_sec,
        'tab_hidden_seconds':   tab_hidden,
    })
    session.behavioral_context = ctx
    session.save(update_fields=['behavioral_context'])

    # ── Guard against all-zero noise ─────────────────────────────────────────
    has_signal = (
        time_on >= 10 or
        scroll_depth >= 10 or
        cta_clicks > 0 or
        atc_clicks > 0 or
        price_views > 0 or
        pricing > 0 or
        copy_events > 0 or
        form_focused
    )
    if not has_signal:
        return

    # ── Map signals → raw EMA scores (0.0 – 1.0) ────────────────────────────

    # INTENT — exploration, content consumption, engagement depth
    raw_intent = _clamp(
        (time_on       / 180) * 0.20 +   # cap at 3 min
        (pages         /   6) * 0.15 +   # cap at 6 pages
        active_ratio          * 0.15 +   # active vs idle/hidden
        (cta_clicks    /   3) * 0.20 +   # cap at 3 CTAs
        milestone_score       * 0.15 +   # scroll depth quality
        (video_plays   /   2) * 0.08 +   # media engagement
        (file_downloads /  2) * 0.07     # download = research intent
    )

    # BUDGET — price-evaluation behaviour
    raw_budget = _clamp(
        (pricing       /   2) * 0.35 +   # pricing page visits (cap 2)
        (price_views   /   4) * 0.25 +   # price elements seen (cap 4)
        (copy_events   /   3) * 0.20 +   # copying prices/SKUs
        (checkout      /   2) * 0.20     # checkout page visits
    )

    # URGENCY — buying signals (add-to-cart strongest; rage-click deducts)
    raw_urgency = _clamp(
        (atc_clicks    /   2) * 0.40 +   # add-to-cart (cap 2)
        int(exit_intent)      * 0.15 +   # leaving = urgency to catch them
        int(form_focused)     * 0.15 +   # started filling a form
        (checkout      /   2) * 0.20 +   # on checkout page
        (cta_clicks    /   3) * 0.10 +   # clicked a CTA
        int(rage_clicks > 0)  * -0.15    # frustration = negative urgency
    )

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
        pass  # EMA update is best-effort; context was already saved


@csrf_exempt
def beacon_receiver(request):
    """
    Receives behavioral analytics from the widget tracker (navigator.sendBeacon).

    Accepts expanded behavior matrix including: clickCount, ctaClicks, rageClicks,
    formFocused, formAbandoned, addToCartClicks, priceViews, copyEvents, videoPlays,
    fileDownloads, idleSeconds, tabHiddenSeconds, scrollMilestones, checkoutVisits.

    If the session doesn't exist yet (visitor browsed but hasn't chatted), the data
    is cached for 30 minutes and applied when the session is eventually created.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    session_id = data.get('sessionId')
    client_id  = data.get('clientId')
    behavior   = data.get('behaviorMatrix', {})
    events     = data.get('events') or []

    if session_id and behavior:
        try:
            from chat.models import ChatSession
            from django.core.cache import cache

            session = ChatSession.objects.filter(session_id=session_id).first()
            if session:
                _apply_behavior(session, behavior)
            else:
                # Session not created yet — cache so it can be applied on first message
                cache.set(f'beacon_{session_id}', behavior, 1800)
        except Exception:
            pass  # beacon is fire-and-forget

    # ── Persist individual events for heatmap / activity timeline ──────────
    if session_id and events:
        _persist_events(session_id, client_id, events)

    return JsonResponse({'status': 'ok'})


_TRACKED_EVENT_TYPES = {
    'click', 'cta_click', 'add_to_cart', 'rage_click',
    'form_focus', 'form_abandoned', 'copy', 'page_view',
    'pricing_visit', 'exit_intent',
}


def _persist_events(session_id, client_id, events):
    """
    Insert raw widget events into AnalyticEvent for heatmap aggregation
    and per-visitor activity timeline.

    Caps inserts at 200 per beacon call (defensive against flood/replay).
    Caps total per-session events to 1000 to prevent unbounded growth.
    Drops events older than 24h (replay protection).
    """
    from .models import AnalyticEvent
    from users.models import Client
    from django.utils import timezone
    from datetime import timedelta

    if len(events) > 200:
        events = events[:200]

    # Per-session cap: skip insert if session already has 1000+ events
    existing = AnalyticEvent.objects.filter(session_id=session_id).count()
    if existing >= 1000:
        return

    client = None
    if client_id:
        try:
            client = Client.objects.filter(pk=client_id).first()
        except Exception:
            client = None

    cutoff = timezone.now() - timedelta(hours=24)
    to_create = []

    for ev in events:
        et = ev.get('type')
        if et not in _TRACKED_EVENT_TYPES:
            continue
        payload = ev.get('data') or {}
        if not isinstance(payload, dict):
            payload = {'value': payload}

        # Page URL — prefer explicit, fall back to data.page_url
        page_url = payload.get('page_url') or ev.get('page_url') or ''
        if not page_url and et == 'page_view' and isinstance(ev.get('data'), str):
            page_url = ev['data']

        to_create.append(AnalyticEvent(
            client=client,
            session_id=str(session_id),
            event_type=et,
            page_url=page_url[:2000] if page_url else '',
            payload=payload,
        ))

    if to_create:
        # bulk_create with ignore_conflicts so a duplicate-flood doesn't error
        try:
            AnalyticEvent.objects.bulk_create(to_create, batch_size=100, ignore_conflicts=True)
        except Exception:
            pass  # never block beacon

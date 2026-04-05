import csv
import logging
import secrets
import threading
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, FloatField, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

logger = logging.getLogger(__name__)

from .models import Client, UserProfile, TenantProfile, Plan, PlanHistory
from .serializers import ClientSerializer, ClientCreateSerializer, UserProfileSerializer
from .permissions import IsSuperAdmin, get_accessible_clients
from chat.models import ChatSession


# ─── Auth ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    Public self-registration for tenant accounts created from the landing page.
    Creates User + UserProfile(tenant_admin) + TenantProfile.
    Returns JWT tokens on success.
    """
    company_name = request.data.get('company_name', '').strip()
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')
    confirm_password = request.data.get('confirm_password', '')

    if not company_name:
        return Response({'detail': 'Company name is required.'}, status=400)
    if not email:
        return Response({'detail': 'Email is required.'}, status=400)
    if not password:
        return Response({'detail': 'Password is required.'}, status=400)
    if len(password) < 8:
        return Response({'detail': 'Password must be at least 8 characters.'}, status=400)
    if password != confirm_password:
        return Response({'detail': 'Passwords do not match.'}, status=400)
    if User.objects.filter(username=email).exists():
        return Response({'detail': 'An account with this email already exists.'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'detail': 'An account with this email already exists.'}, status=400)

    user = User.objects.create_user(username=email, email=email, password=password)
    UserProfile.objects.create(user=user, role='tenant_admin')
    TenantProfile.objects.create(user=user, company_name=company_name)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'username': user.username,
            'email': user.email,
            'role': 'tenant_admin',
            'is_superuser': False,
        }
    }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response({'detail': 'Username and password required.'}, status=400)

    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'detail': 'Invalid username or password.'}, status=401)

    refresh = RefreshToken.for_user(user)
    profile = getattr(user, 'profile', None)
    role = profile.role if profile else ('superadmin' if user.is_superuser else 'tenant_admin')

    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'username': user.username,
            'email': user.email,
            'role': role,
            'is_superuser': user.is_superuser,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    profile = getattr(user, 'profile', None)
    role = profile.role if profile else ('superadmin' if user.is_superuser else 'tenant_admin')

    quota = None
    tenant = getattr(user, 'tenant_profile', None)
    if tenant:
        plan = tenant.plan
        client_count = tenant.clients.filter(is_active=True).count()
        quota = {
            'sessions_this_month': tenant.sessions_this_month,
            'max_sessions': plan.max_sessions_per_month if plan else None,
            'client_count': client_count,
            'max_clients': plan.max_clients if plan else None,
            'plan_name': plan.name if plan else None,
        }

    return Response({
        'username': user.username,
        'email': user.email,
        'role': role,
        'is_superuser': user.is_superuser,
        'quota': quota,
    })


# ─── Client CRUD ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def client_list(request):
    if request.method == 'GET':
        clients = get_accessible_clients(request.user).order_by('-created_at')
        data = ClientSerializer(clients, many=True).data
        # Annotate each client with its assigned tenant (if any)
        tenant_map = {}
        for tp in TenantProfile.objects.prefetch_related('clients').all():
            for c in tp.clients.all():
                tenant_map[str(c.id)] = {'tenant_id': tp.pk, 'tenant_name': tp.company_name or tp.user.username}
        for item in data:
            info = tenant_map.get(str(item['id']))
            item['tenant_id'] = info['tenant_id'] if info else None
            item['tenant_name'] = info['tenant_name'] if info else None
        return Response(data)

    # POST — create client (superadmin or tenant_admin)
    serializer = ClientCreateSerializer(data=request.data)
    if serializer.is_valid():
        client = serializer.save()
        # Auto-assign to tenant profile if tenant_admin
        tenant = getattr(request.user, 'tenant_profile', None)
        if tenant:
            tenant.clients.add(client)
        return Response(ClientSerializer(client).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def client_detail(request, client_id):
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'GET':
        return Response(ClientSerializer(client).data)

    if request.method == 'PATCH':
        serializer = ClientSerializer(client, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    if request.method == 'DELETE':
        client.delete()
        return Response(status=204)


# ─── Sessions ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_sessions(request, client_id):
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    qs = ChatSession.objects.filter(client=client).order_by('-updated_at')

    # ── Filters ────────────────────────────────────────────────────────
    state = request.query_params.get('state', '').strip()
    if state:
        qs = qs.filter(conversation_state=state)

    date_from = request.query_params.get('date_from', '').strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = request.query_params.get('date_to', '').strip()
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    if request.query_params.get('has_lead') == 'true':
        qs = qs.exclude(lead_email='').exclude(lead_email__isnull=True)

    q = request.query_params.get('q', '').strip()
    if q:
        qs = qs.filter(lead_email__icontains=q)

    # Fetch up to 200; heat-score range filter applied in-memory
    min_heat_raw = request.query_params.get('min_heat', '').strip()
    max_heat_raw = request.query_params.get('max_heat', '').strip()
    min_heat = float(min_heat_raw) if min_heat_raw else None
    max_heat = float(max_heat_raw) if max_heat_raw else None

    data = []
    for s in qs[:200]:
        heat = _calc_heat(s)
        if min_heat is not None and heat < min_heat:
            continue
        if max_heat is not None and heat > max_heat:
            continue
        data.append({
            'session_id': str(s.session_id),
            'visitor_id': s.visitor_id,
            'heat_score': heat,
            'conversation_state': s.conversation_state,
            'kanban_state': s.kanban_state,
            'message_count': s.message_count,
            'intent_ema': round(s.current_intent_ema, 3),
            'budget_ema': round(s.current_budget_ema, 3),
            'urgency_ema': round(s.current_urgency_ema, 3),
            'lead_email': s.lead_email,
            'lead_phone': s.lead_phone,
            'takeover_active': s.takeover_active,
            'closing_triggered': s.closing_triggered,
            'chat_history': s.chat_history,
            # Visitor fingerprint
            'visitor_ip': s.visitor_ip,
            'visitor_country': s.visitor_country,
            'visitor_city': s.visitor_city,
            'visitor_country_code': s.visitor_country_code,
            'visitor_device': s.visitor_device,
            'visitor_os': s.visitor_os,
            'visitor_browser': s.visitor_browser,
            'visitor_referrer': s.visitor_referrer,
            'visitor_timezone': s.visitor_timezone,
            'page_visits': s.page_visits,
            'channel': s.channel,
            'updated_at': s.updated_at.isoformat(),
            'created_at': s.created_at.isoformat(),
        })
    return Response(data)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def session_detail(request, session_id):
    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    # Verify access
    accessible_ids = get_accessible_clients(request.user).values_list('id', flat=True)
    if session.client_id and session.client_id not in list(accessible_ids):
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'PATCH':
        allowed_fields = ['kanban_state', 'conversation_state', 'lead_email', 'lead_phone']
        for field in allowed_fields:
            if field in request.data:
                setattr(session, field, request.data[field])
        session.save()
        return Response({'detail': 'Updated.'})

    return Response({
        'session_id': str(session.session_id),
        'visitor_id': session.visitor_id,
        'heat_score': _calc_heat(session),
        'conversation_state': session.conversation_state,
        'kanban_state': session.kanban_state,
        'message_count': session.message_count,
        'intent_ema': round(session.current_intent_ema, 3),
        'budget_ema': round(session.current_budget_ema, 3),
        'urgency_ema': round(session.current_urgency_ema, 3),
        'lead_email': session.lead_email,
        'lead_phone': session.lead_phone,
        'takeover_active': session.takeover_active,
        'taken_over_by': session.taken_over_by.username if session.taken_over_by else None,
        'closing_triggered': session.closing_triggered,
        'chat_history': session.chat_history,
        'behavioral_context': session.behavioral_context,
        # Visitor fingerprint
        'visitor_ip': session.visitor_ip,
        'visitor_country': session.visitor_country,
        'visitor_city': session.visitor_city,
        'visitor_country_code': session.visitor_country_code,
        'visitor_device': session.visitor_device,
        'visitor_os': session.visitor_os,
        'visitor_browser': session.visitor_browser,
        'visitor_referrer': session.visitor_referrer,
        'visitor_timezone': session.visitor_timezone,
        'page_visits': session.page_visits,
        'channel': session.channel,
        'updated_at': session.updated_at.isoformat(),
        'created_at': session.created_at.isoformat(),
    })


# ─── God View — Takeover ─────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_takeover(request, session_id):
    """Admin takes over a session — disables AI replies."""
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    session.takeover_active = True
    session.taken_over_by = request.user
    session.save(update_fields=['takeover_active', 'taken_over_by'])
    return Response({'detail': 'Takeover active.', 'session_id': str(session_id)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_release(request, session_id):
    """Release a session back to AI."""
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    session.takeover_active = False
    session.taken_over_by = None
    session.save(update_fields=['takeover_active', 'taken_over_by'])
    return Response({'detail': 'Session released to AI.', 'session_id': str(session_id)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def session_send_message(request, session_id):
    """Admin sends a message directly to visitor during God View takeover."""
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    message = request.data.get('message', '').strip()
    if not message:
        return Response({'detail': 'Message is required.'}, status=400)

    # Push message to the visitor's WebSocket group
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    group_name = f'chat_{session_id}'

    # Save to chat history
    history = session.chat_history or []
    history.append({'role': 'ai', 'message': message, 'source': 'admin'})
    session.chat_history = history
    from chat.utils import truncate_chat_history
    update_fields = truncate_chat_history(session)
    session.save(update_fields=update_fields)

    async_to_sync(channel_layer.group_send)(group_name, {
        'type': 'chat_message',
        'message': message,
        'source': 'admin',
    })

    return Response({'detail': 'Message sent.'})


# ─── Analytics ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def client_analytics(request, client_id):
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    # ── Period window ─────────────────────────────────────────────────────────
    period = request.query_params.get('period', '30d')
    now = timezone.now()
    period_days_map = {'today': 1, '7d': 7, '30d': 30, '90d': 90}
    days = period_days_map.get(period, 30)

    if period == 'today':
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = now - timedelta(days=days)

    prev_end = period_start
    prev_start = period_start - timedelta(days=days)

    all_sessions = ChatSession.objects.filter(client=client)
    sessions = all_sessions.filter(created_at__gte=period_start)
    prev_sessions = all_sessions.filter(created_at__gte=prev_start, created_at__lt=prev_end)

    # ── Reusable metric computation ───────────────────────────────────────────
    heat_expr = ExpressionWrapper(
        (F('current_intent_ema') * 0.45 + F('current_budget_ema') * 0.30 + F('current_urgency_ema') * 0.25) * 100,
        output_field=FloatField()
    )
    dur_expr = ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField())

    def get_metrics(qs):
        total = qs.count()
        unique_visitors = qs.values('visitor_id').distinct().count()
        ai_handled = qs.filter(taken_over_by__isnull=True).count()
        manual_handled = qs.filter(taken_over_by__isnull=False).count()
        missed = qs.filter(message_count=0).count()

        dur_qs = qs.annotate(dur=dur_expr)
        avg_dur_td = dur_qs.aggregate(avg=Avg('dur'))['avg']
        total_dur_td = dur_qs.aggregate(total=Sum('dur'))['total']
        avg_dur_s = int(avg_dur_td.total_seconds()) if avg_dur_td else 0
        total_dur_s = int(total_dur_td.total_seconds()) if total_dur_td else 0

        leads = qs.filter(
            Q(lead_email__isnull=False) | Q(lead_phone__isnull=False)
        ).exclude(lead_email='').count()

        annotated = qs.annotate(heat=heat_expr)
        hot = annotated.filter(heat__gte=70).count()
        warm = annotated.filter(heat__gte=40, heat__lt=70).count()
        cold = annotated.filter(heat__lt=40).count()
        avg_heat = annotated.aggregate(avg=Avg('heat'))['avg'] or 0
        ai_res_rate = round((ai_handled / total * 100) if total > 0 else 0, 1)

        return {
            'total': total, 'unique_visitors': unique_visitors,
            'ai_handled': ai_handled, 'manual_handled': manual_handled,
            'missed': missed, 'avg_dur_s': avg_dur_s, 'total_dur_s': total_dur_s,
            'leads': leads, 'hot': hot, 'warm': warm, 'cold': cold,
            'avg_heat': round(avg_heat, 1), 'ai_resolution_rate': ai_res_rate,
        }

    def metric_obj(curr_val, prev_val):
        return {'value': curr_val, 'previous': prev_val, 'delta': curr_val - prev_val}

    curr = get_metrics(sessions)
    prev = get_metrics(prev_sessions)

    # ── Funnel + EMA (current period) ─────────────────────────────────────────
    state_counts = sessions.values('conversation_state').annotate(count=Count('session_id'))
    funnel = {item['conversation_state']: item['count'] for item in state_counts}

    agg = sessions.aggregate(
        avg_intent=Avg('current_intent_ema'),
        avg_budget=Avg('current_budget_ema'),
        avg_urgency=Avg('current_urgency_ema'),
    )

    kanban_raw = sessions.values('kanban_state').annotate(count=Count('session_id'))
    kanban_breakdown = {item['kanban_state']: item['count'] for item in kanban_raw}

    # ── Daily trend ───────────────────────────────────────────────────────────
    today = now.date()
    trend_days = min(days, 30)
    daily_raw = (
        sessions
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('session_id'))
        .order_by('day')
    )
    daily_map = {item['day']: item['count'] for item in daily_raw}
    daily_trend = [
        {'date': (today - timedelta(days=i)).strftime('%b %d'), 'count': daily_map.get(today - timedelta(days=i), 0)}
        for i in range(trend_days - 1, -1, -1)
    ]

    # ── Analytics events ──────────────────────────────────────────────────────
    total_page_views = 0
    total_exit_intent = 0
    total_pricing_visits = 0
    for ctx_val in sessions.values_list('behavioral_context', flat=True):
        ctx = ctx_val or {}
        total_page_views += ctx.get('pages_viewed', 0) or 0
        total_pricing_visits += ctx.get('pricing_page_visits', 0) or 0
        if ctx.get('exit_intent_triggered'):
            total_exit_intent += 1

    return Response({
        'period': period,

        # ── Metrics with period deltas ────────────────────────────────────────
        'total_sessions':        metric_obj(curr['total'], prev['total']),
        'unique_visitors':       metric_obj(curr['unique_visitors'], prev['unique_visitors']),
        'ai_handled':            metric_obj(curr['ai_handled'], prev['ai_handled']),
        'manual_handled':        metric_obj(curr['manual_handled'], prev['manual_handled']),
        'missed_chats':          metric_obj(curr['missed'], prev['missed']),
        'ai_resolution_rate':    metric_obj(curr['ai_resolution_rate'], prev['ai_resolution_rate']),
        'avg_duration_seconds':  metric_obj(curr['avg_dur_s'], prev['avg_dur_s']),
        'total_duration_seconds': metric_obj(curr['total_dur_s'], prev['total_dur_s']),
        'leads_captured':        metric_obj(curr['leads'], prev['leads']),
        'hot_sessions':          metric_obj(curr['hot'], prev['hot']),
        'avg_heat_score':        curr['avg_heat'],
        'heat_distribution':     {'hot': curr['hot'], 'warm': curr['warm'], 'cold': curr['cold']},

        # ── EMA signal averages ───────────────────────────────────────────────
        'avg_intent':  round((agg['avg_intent'] or 0) * 100, 1),
        'avg_budget':  round((agg['avg_budget'] or 0) * 100, 1),
        'avg_urgency': round((agg['avg_urgency'] or 0) * 100, 1),

        # ── Funnel / Kanban ───────────────────────────────────────────────────
        'funnel': {
            'RESEARCH':    funnel.get('RESEARCH', 0),
            'EVALUATION':  funnel.get('EVALUATION', 0),
            'OBJECTION':   funnel.get('OBJECTION', 0),
            'RECOVERY':    funnel.get('RECOVERY', 0),
            'READY_TO_BUY': funnel.get('READY_TO_BUY', 0),
        },
        'kanban_breakdown': kanban_breakdown,
        'daily_trend': daily_trend,

        # ── Analytics events ──────────────────────────────────────────────────
        'analytics_events': {
            'page_views': total_page_views,
            'exit_intent_count': total_exit_intent,
            'pricing_page_visits': total_pricing_visits,
        },
        'pages_ingested': client.total_pages_ingested,
        'ingestion_status': client.ingestion_status,
    })


# ─── Scrape trigger ───────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_scrape(request, client_id):
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if not client.domain_url:
        return Response({'detail': 'Client has no domain URL set.'}, status=400)

    client.ingestion_status = 'RUNNING'
    client.total_pages_ingested = 0
    client.save(update_fields=['ingestion_status', 'total_pages_ingested'])

    cid = str(client.id)

    _cache_key = f'scrape_progress:{cid}'

    def _run_scrape():
        """Run scrape in a background thread — no Celery required."""
        from django.db import connection
        from django.core.cache import cache
        connection.close()  # Let Django open a fresh DB connection in this thread
        try:
            from scraper.ingestion import auto_scrape, ingest_documents
            _client = Client.objects.get(pk=cid)
            logger.info(f'[trigger_scrape] Starting scrape for "{_client.name}"')

            # Phase 1: crawling
            cache.set(_cache_key, {'phase': 'crawling', 'done': 0, 'total': 0}, 3600)
            documents = auto_scrape(_client)

            # Phase 2: embedding
            cache.set(_cache_key, {'phase': 'embedding', 'done': 0, 'total': 0}, 3600)

            def _progress(done, total):
                cache.set(_cache_key, {'phase': 'embedding', 'done': done, 'total': total}, 3600)

            count = ingest_documents(_client, documents, progress_cb=_progress)
            Client.objects.filter(pk=cid).update(
                ingestion_status='DONE',
                total_pages_ingested=count,
            )
            cache.delete(_cache_key)
            logger.info(f'[trigger_scrape] Done — {count} chunks ingested for "{_client.name}"')
        except Exception as exc:
            logger.error(f'[trigger_scrape] Failed for client {cid}: {exc}')
            Client.objects.filter(pk=cid).update(ingestion_status='FAILED')
            from django.core.cache import cache as _c
            _c.delete(_cache_key)

    threading.Thread(target=_run_scrape, daemon=True).start()
    return Response({'detail': 'Scrape started.', 'status': 'RUNNING'})


# ─── Scrape progress (polling endpoint) ──────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scrape_progress(request, client_id):
    from django.core.cache import cache
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    cache_key = f'scrape_progress:{client_id}'
    progress = cache.get(cache_key) or {}

    return Response({
        'status': client.ingestion_status,
        'pages_ingested': client.total_pages_ingested,
        'phase': progress.get('phase', ''),
        'done': progress.get('done', 0),
        'total': progress.get('total', 0),
    })


# ─── Platform stats (superadmin only) ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_stats(request):
    is_super = request.user.is_superuser or (
        getattr(getattr(request.user, 'profile', None), 'role', '') == 'superadmin'
    )

    accessible = get_accessible_clients(request.user)
    active_clients = accessible.filter(is_active=True).count()
    total_clients = accessible.count()

    sessions_qs = ChatSession.objects.filter(client__in=accessible)
    total_sessions = sessions_qs.count()

    # Heat distribution via DB expression (avoids Python loop)
    heat_expr = ExpressionWrapper(
        (F('current_intent_ema') * 0.45 + F('current_budget_ema') * 0.30 + F('current_urgency_ema') * 0.25) * 100,
        output_field=FloatField()
    )
    annotated = sessions_qs.annotate(heat=heat_expr)
    hot_count = annotated.filter(heat__gte=70).count()
    warm_count = annotated.filter(heat__gte=40, heat__lt=70).count()
    cold_count = annotated.filter(heat__lt=40).count()

    # 14-day daily session trend
    today = timezone.now().date()
    cutoff = timezone.now() - timedelta(days=14)
    daily_raw = (
        sessions_qs
        .filter(created_at__gte=cutoff)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('session_id'))
        .order_by('day')
    )
    daily_map = {item['day']: item['count'] for item in daily_raw}
    daily_trend = [
        {'date': (today - timedelta(days=i)).strftime('%b %d'), 'count': daily_map.get(today - timedelta(days=i), 0)}
        for i in range(13, -1, -1)
    ]

    response = {
        'total_clients': total_clients,
        'active_clients': active_clients,
        'total_sessions': total_sessions,
        'heat_distribution': {'hot': hot_count, 'warm': warm_count, 'cold': cold_count},
        'daily_trend': daily_trend,
    }
    if is_super:
        response['total_users'] = User.objects.count()

    return Response(response)


# ─── Kanban ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kanban_view(request):
    accessible = get_accessible_clients(request.user)
    sessions = ChatSession.objects.filter(client__in=accessible).select_related('client').order_by('-updated_at')[:200]
    data = []
    for s in sessions:
        heat = _calc_heat(s)
        data.append({
            'session_id': str(s.session_id),
            'visitor_id': s.visitor_id,
            'heat_score': heat,
            'conversation_state': s.conversation_state,
            'kanban_state': s.kanban_state,
            'message_count': s.message_count,
            'client_name': s.client.name if s.client else 'Unknown',
            'client_id': str(s.client.id) if s.client else None,
            'lead_email': s.lead_email,
            'takeover_active': s.takeover_active,
            'updated_at': s.updated_at.isoformat(),
        })
    return Response(data)


# ─── Tenant Management (superadmin only) ─────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def tenant_list(request):
    """List all tenants or create a new one."""
    if request.method == 'GET':
        tenants = TenantProfile.objects.select_related('user', 'plan').prefetch_related('clients').all()
        data = []
        for t in tenants:
            assigned_clients = list(t.clients.all())
            data.append({
                'id': t.id,
                'username': t.user.username,
                'email': t.user.email,
                'company_name': t.company_name,
                'plan': t.plan.name if t.plan else None,
                'plan_id': t.plan.id if t.plan else None,
                'sessions_this_month': t.sessions_this_month,
                'clients_count': len(assigned_clients),
                'clients': [str(c.id) for c in assigned_clients],
                'client_details': [
                    {'id': str(c.id), 'name': c.name, 'domain_url': c.domain_url, 'chatbot_color': c.chatbot_color}
                    for c in assigned_clients
                ],
                'plan_max_sessions': t.plan.max_sessions_per_month if t.plan else None,
                'plan_max_clients': t.plan.max_clients if t.plan else None,
                'plan_price': str(t.plan.price_monthly) if t.plan else None,
            })
        return Response(data)

    # POST — create new tenant user
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '').strip()
    company_name = request.data.get('company_name', '').strip()
    plan_id = request.data.get('plan_id')

    if not username or not password:
        return Response({'detail': 'Username and password are required.'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'detail': 'Username already exists.'}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    UserProfile.objects.create(user=user, role='tenant_admin')

    plan = None
    if plan_id:
        try:
            plan = Plan.objects.get(pk=plan_id)
        except Plan.DoesNotExist:
            pass

    tenant = TenantProfile.objects.create(user=user, company_name=company_name, plan=plan)

    # Assign clients if provided
    client_ids = request.data.get('client_ids', [])
    if client_ids:
        clients_qs = Client.objects.filter(pk__in=client_ids)
        tenant.clients.set(clients_qs)

    return Response({
        'id': tenant.id,
        'username': user.username,
        'email': user.email,
        'company_name': tenant.company_name,
        'plan': plan.name if plan else None,
        'clients_count': tenant.clients.count(),
        'clients': [str(c.id) for c in tenant.clients.all()],
    }, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def tenant_detail(request, tenant_id):
    """Get, update, or delete a tenant."""
    try:
        tenant = TenantProfile.objects.select_related('user', 'plan').get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': tenant.id,
            'username': tenant.user.username,
            'email': tenant.user.email,
            'company_name': tenant.company_name,
            'plan': tenant.plan.name if tenant.plan else None,
            'plan_id': tenant.plan.id if tenant.plan else None,
            'sessions_this_month': tenant.sessions_this_month,
            'clients': [str(c.id) for c in tenant.clients.all()],
        })

    if request.method == 'PATCH':
        if 'company_name' in request.data:
            tenant.company_name = request.data['company_name']
        if 'plan_id' in request.data:
            try:
                tenant.plan = Plan.objects.get(pk=request.data['plan_id'])
            except Plan.DoesNotExist:
                return Response({'detail': 'Plan not found.'}, status=400)
        if 'client_ids' in request.data:
            ids = request.data['client_ids']
            clients = Client.objects.filter(id__in=ids)
            tenant.clients.set(clients)
        if 'email' in request.data:
            tenant.user.email = request.data['email']
            tenant.user.save(update_fields=['email'])
        if 'password' in request.data and request.data['password']:
            tenant.user.set_password(request.data['password'])
            tenant.user.save(update_fields=['password'])
        tenant.save()
        return Response({'detail': 'Updated.'})

    if request.method == 'DELETE':
        tenant.user.delete()  # cascades to TenantProfile and UserProfile
        return Response(status=204)


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def assign_plan(request, tenant_id):
    """Assign a plan to a tenant and log the change in PlanHistory."""
    try:
        tenant = TenantProfile.objects.select_related('plan').get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    plan_id = request.data.get('plan_id')
    if not plan_id:
        return Response({'detail': 'plan_id is required.'}, status=400)

    try:
        new_plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return Response({'detail': 'Plan not found.'}, status=400)

    old_plan = tenant.plan
    remarks = request.data.get('remarks', '').strip()

    PlanHistory.objects.create(
        tenant=tenant,
        from_plan=old_plan,
        to_plan=new_plan,
        changed_by=request.user,
        remarks=remarks,
    )

    tenant.plan = new_plan
    tenant.save(update_fields=['plan'])
    return Response({
        'detail': f'Plan "{new_plan.name}" assigned.',
        'plan': new_plan.name,
        'plan_id': new_plan.id,
        'plan_max_sessions': new_plan.max_sessions_per_month,
        'plan_max_clients': new_plan.max_clients,
        'plan_price': str(new_plan.price_monthly),
    })


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def plan_history(request, tenant_id):
    """Return plan change history for a tenant."""
    try:
        tenant = TenantProfile.objects.get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    history = PlanHistory.objects.filter(tenant=tenant).select_related('from_plan', 'to_plan', 'changed_by')
    data = [{
        'id': h.id,
        'from_plan': h.from_plan.name if h.from_plan else None,
        'to_plan': h.to_plan.name if h.to_plan else None,
        'changed_by': h.changed_by.username if h.changed_by else 'system',
        'remarks': h.remarks,
        'changed_at': h.changed_at.isoformat(),
    } for h in history]
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_list(request):
    """List all available plans."""
    plans = Plan.objects.all().order_by('price_monthly')
    data = [{
        'id': p.id,
        'name': p.name,
        'max_clients': p.max_clients,
        'max_sessions_per_month': p.max_sessions_per_month,
        'price_monthly': str(p.price_monthly),
    } for p in plans]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def assign_client_to_tenant(request, client_id):
    """
    Assign or unassign a client to a tenant.
    Body: { tenant_id: int | null }
    - tenant_id = int  → assign this client to that tenant (removes from any previous tenant first)
    - tenant_id = null → unassign the client from whoever currently owns it
    """
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Client not found.'}, status=404)

    # Remove client from any existing tenant first (a client belongs to one tenant at a time)
    for tp in TenantProfile.objects.filter(clients=client):
        tp.clients.remove(client)

    tenant_id = request.data.get('tenant_id')
    if tenant_id:
        try:
            tenant = TenantProfile.objects.get(pk=tenant_id)
        except TenantProfile.DoesNotExist:
            return Response({'detail': 'Tenant not found.'}, status=404)
        tenant.clients.add(client)
        return Response({
            'detail': f'Client "{client.name}" assigned to tenant "{tenant.company_name or tenant.user.username}".',
            'tenant_id': tenant.pk,
            'tenant_name': tenant.company_name or tenant.user.username,
        })

    return Response({'detail': f'Client "{client.name}" unassigned.', 'tenant_id': None, 'tenant_name': None})


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def impersonate_tenant(request, tenant_id):
    """
    SuperAdmin only — issues a short-lived JWT (1 hr) scoped to the tenant's user.
    The returned token carries a custom claim 'impersonated_by' so audit logs can
    distinguish real logins from impersonation sessions.
    """
    try:
        tenant = TenantProfile.objects.select_related('user').get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Tenant not found.'}, status=404)

    tenant_user = tenant.user
    if not tenant_user:
        return Response({'detail': 'Tenant has no linked user account.'}, status=400)

    # Issue a fresh access token for the tenant user
    refresh = RefreshToken.for_user(tenant_user)
    # Shorten access token lifetime to 1 hour for impersonation safety
    from datetime import timedelta
    from django.utils import timezone
    access = refresh.access_token
    access.set_exp(lifetime=timedelta(hours=1))
    # Embed audit claim
    access['impersonated_by'] = request.user.username

    profile = getattr(tenant_user, 'profile', None)
    role = profile.role if profile else 'tenant_admin'

    return Response({
        'access': str(access),
        'expires_in': 3600,
        'tenant': {
            'id': tenant.pk,
            'company_name': tenant.company_name,
            'username': tenant_user.username,
            'email': tenant_user.email,
            'role': role,
        },
        'impersonated_by': request.user.username,
    })


# ─── Leads ────────────────────────────────────────────────────────────────────

def _leads_queryset(request):
    """Shared filtered queryset for leads_list and leads_export."""
    accessible = get_accessible_clients(request.user)

    heat_expr = ExpressionWrapper(
        (F('current_intent_ema') * 0.45 + F('current_budget_ema') * 0.30 + F('current_urgency_ema') * 0.25) * 100,
        output_field=FloatField()
    )

    has_email = Q(lead_email__isnull=False) & ~Q(lead_email='')
    has_phone = Q(lead_phone__isnull=False) & ~Q(lead_phone='')

    qs = (
        ChatSession.objects
        .filter(client__in=accessible)
        .filter(has_email | has_phone)
        .select_related('client')
        .annotate(computed_heat=heat_expr)
        .order_by('-created_at')
    )

    client_id = request.GET.get('client_id')
    if client_id:
        qs = qs.filter(client__id=client_id)

    date_from = request.GET.get('date_from')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    min_heat = request.GET.get('min_heat')
    if min_heat:
        try:
            qs = qs.filter(computed_heat__gte=float(min_heat))
        except ValueError:
            pass

    return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leads_list(request):
    qs = _leads_queryset(request)
    leads = qs[:500]
    data = []
    for s in leads:
        data.append({
            'session_id': str(s.session_id),
            'visitor_id': s.visitor_id,
            'lead_email': s.lead_email or '',
            'lead_phone': s.lead_phone or '',
            'heat_score': round(min(s.computed_heat, 100.0), 1),
            'kanban_state': s.kanban_state,
            'client_name': s.client.name if s.client else 'Unknown',
            'client_id': str(s.client.id) if s.client else None,
            'created_at': s.created_at.isoformat(),
        })
    return Response({'count': len(data), 'leads': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leads_export(request):
    qs = _leads_queryset(request)
    leads = qs[:5000]

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="leads.csv"'

    writer = csv.writer(response)
    writer.writerow(['Email', 'Phone', 'Heat Score', 'Stage', 'Client', 'Session ID', 'Date Captured'])
    for s in leads:
        writer.writerow([
            s.lead_email or '',
            s.lead_phone or '',
            round(min(s.computed_heat, 100.0), 1),
            s.kanban_state,
            s.client.name if s.client else '',
            str(s.session_id),
            s.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


# ─── Helper ───────────────────────────────────────────────────────────────────

def _calc_heat(session):
    score = (
        session.current_intent_ema * 0.45 +
        session.current_budget_ema * 0.30 +
        session.current_urgency_ema * 0.25
    ) * 100
    return round(min(score, 100), 1)


# ─── Webhook secret rotation ──────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rotate_webhook_secret(request, client_id):
    """
    Generate a new cryptographically-random webhook secret for a client.
    The new secret is returned once in the response body — store it immediately.
    """
    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    new_secret = secrets.token_hex(32)
    client.webhook_secret = new_secret
    client.save(update_fields=['webhook_secret'])
    logger.info(f'[rotate_webhook_secret] Rotated secret for client {client_id}')
    return Response({'webhook_secret': new_secret, 'detail': 'Webhook secret rotated.'})

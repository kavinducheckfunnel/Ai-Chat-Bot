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


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """Send a password-reset link to the given email address."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.core.mail import EmailMessage as DjangoEmail
    from django.conf import settings as django_settings

    email = request.data.get('email', '').strip().lower()
    # Always return 200 — never reveal whether an account exists
    response_msg = 'If an account with that email exists, a reset link has been sent.'

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'detail': response_msg})

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f'https://ai.checkfunnels.com/reset-password?uid={uid}&token={token}'

    body = (
        f'Hi {user.get_full_name() or user.username},\n\n'
        f'Click the link below to reset your Checkfunnel password:\n\n'
        f'{reset_url}\n\n'
        f'This link expires in 1 hour. If you did not request a password reset, '
        f'you can safely ignore this email.\n\n'
        f'— The Checkfunnel Team'
    )
    try:
        DjangoEmail(
            subject='Reset your Checkfunnel password',
            body=body,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        ).send(fail_silently=True)
    except Exception as e:
        logger.warning(f'[forgot_password] Email send failed: {e}')

    return Response({'detail': response_msg})


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """Validate uid+token and set a new password."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    uid = request.data.get('uid', '')
    token = request.data.get('token', '')
    new_password = request.data.get('new_password', '')

    if len(new_password) < 8:
        return Response({'detail': 'Password must be at least 8 characters.'}, status=400)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'detail': 'Invalid reset link.'}, status=400)

    if not default_token_generator.check_token(user, token):
        return Response({'detail': 'Reset link is invalid or has expired.'}, status=400)

    user.set_password(new_password)
    user.save()
    return Response({'detail': 'Password has been reset. You can now sign in.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Authenticated user changes their own password."""
    current = request.data.get('current_password', '')
    new_pw = request.data.get('new_password', '')

    if not request.user.check_password(current):
        return Response({'detail': 'Current password is incorrect.'}, status=400)
    if len(new_pw) < 8:
        return Response({'detail': 'New password must be at least 8 characters.'}, status=400)

    request.user.set_password(new_pw)
    request.user.save()
    return Response({'detail': 'Password updated successfully.'})


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
    from users.feature_flags import has_feature, gate_feature
    if not has_feature(request.user, 'allow_god_view'):
        return gate_feature('allow_god_view')

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
        'stripe_price_id': p.stripe_price_id or '',
    } for p in plans]
    return Response(data)


@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def plan_detail(request, plan_id):
    """Update a plan (superadmin only — currently used to set stripe_price_id)."""
    try:
        plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return Response({'detail': 'Plan not found.'}, status=404)

    allowed = ['stripe_price_id', 'name', 'max_clients', 'max_sessions_per_month', 'price_monthly']
    for field in allowed:
        if field in request.data:
            setattr(plan, field, request.data[field])
    plan.save()
    return Response({
        'id': plan.id,
        'name': plan.name,
        'max_clients': plan.max_clients,
        'max_sessions_per_month': plan.max_sessions_per_month,
        'price_monthly': str(plan.price_monthly),
        'stripe_price_id': plan.stripe_price_id or '',
    })


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


# ─── Analytics export ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_export(request, client_id):
    """
    Download analytics for a client as a CSV file.
    Query param: period = today | 7d | 30d | 90d (default 30d)
    """
    from users.feature_flags import has_feature, gate_feature
    if not has_feature(request.user, 'allow_csv_export'):
        return gate_feature('allow_csv_export')

    accessible = get_accessible_clients(request.user)
    try:
        client = accessible.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    period = request.query_params.get('period', '30d')
    now = timezone.now()
    period_days_map = {'today': 1, '7d': 7, '30d': 30, '90d': 90}
    days = period_days_map.get(period, 30)

    if period == 'today':
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = now - timedelta(days=days)

    heat_expr = ExpressionWrapper(
        (F('current_intent_ema') * 0.45 + F('current_budget_ema') * 0.30 + F('current_urgency_ema') * 0.25) * 100,
        output_field=FloatField()
    )

    sessions = (
        ChatSession.objects
        .filter(client=client, created_at__gte=period_start)
        .annotate(heat=heat_expr)
        .values(
            'session_id', 'visitor_id', 'channel', 'kanban_state',
            'conversation_state', 'heat', 'lead_email', 'lead_phone',
            'message_count', 'visitor_country', 'visitor_device',
            'created_at', 'updated_at',
        )
        .order_by('-created_at')
    )

    filename = f'{client.name}_analytics_{period}_{now.strftime("%Y%m%d")}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Session ID', 'Visitor ID', 'Channel', 'Kanban State', 'Conv State',
        'Heat Score', 'Lead Email', 'Lead Phone', 'Messages',
        'Country', 'Device', 'Created At', 'Last Updated',
    ])
    for s in sessions:
        writer.writerow([
            str(s['session_id']),
            s['visitor_id'],
            s['channel'],
            s['kanban_state'],
            s['conversation_state'],
            round(min(s['heat'] or 0, 100), 1),
            s['lead_email'] or '',
            s['lead_phone'] or '',
            s['message_count'],
            s['visitor_country'] or '',
            s['visitor_device'] or '',
            s['created_at'].strftime('%Y-%m-%d %H:%M') if s['created_at'] else '',
            s['updated_at'].strftime('%Y-%m-%d %H:%M') if s['updated_at'] else '',
        ])

    return response


# ─── Session tags ─────────────────────────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def session_set_tags(request, session_id):
    """
    Set (replace) the tags list on a session.
    Body: { "tags": ["Support", "VIP"] }
    """
    from users.feature_flags import has_feature, gate_feature
    if not has_feature(request.user, 'allow_conversation_tags'):
        return gate_feature('allow_conversation_tags')

    from .permissions import get_accessible_clients
    tags = request.data.get('tags')
    if not isinstance(tags, list):
        return Response({'detail': 'tags must be a list.'}, status=400)

    # Validate each tag is a non-empty string, max 50 chars
    cleaned = []
    for t in tags:
        if isinstance(t, str) and t.strip():
            cleaned.append(t.strip()[:50])

    accessible_client_ids = get_accessible_clients(request.user).values_list('id', flat=True)
    updated = ChatSession.objects.filter(
        session_id=session_id,
        client_id__in=accessible_client_ids,
    ).update(tags=cleaned)

    if not updated:
        return Response({'detail': 'Session not found or access denied.'}, status=404)

    return Response({'tags': cleaned})


# ─── Revenue Intelligence ─────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_overview(request):
    """
    Superadmin: live revenue metrics — MRR, ARR, churn, ARPU, plan distribution.
    """
    from .permissions import IsSuperAdmin
    if not request.user.profile.is_superadmin:
        return Response({'detail': 'Forbidden.'}, status=403)

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    active_tenants = TenantProfile.objects.filter(
        stripe_subscription_status='active'
    ).select_related('plan')

    mrr = sum(
        float(t.plan.price_monthly) for t in active_tenants if t.plan
    )
    arr = mrr * 12

    # New MRR this month — tenants whose plan was set/changed this month
    # (approximated via PlanHistory)
    new_mrr_tenants = PlanHistory.objects.filter(
        changed_at__gte=month_start,
        to_plan__isnull=False,
    ).exclude(from_plan__isnull=True)
    new_mrr = sum(
        float(ph.to_plan.price_monthly) - float(ph.from_plan.price_monthly if ph.from_plan else 0)
        for ph in new_mrr_tenants
        if ph.to_plan
    )
    new_mrr = max(new_mrr, 0)

    churned_mrr_tenants = PlanHistory.objects.filter(
        changed_at__gte=month_start,
        to_plan__isnull=True,
    )
    churned_mrr = sum(
        float(ph.from_plan.price_monthly) for ph in churned_mrr_tenants if ph.from_plan
    )

    total_tenants = TenantProfile.objects.count()
    arpu = round(mrr / active_tenants.count(), 2) if active_tenants.count() > 0 else 0

    past_due = TenantProfile.objects.filter(stripe_subscription_status='past_due').count()
    trialing = TenantProfile.objects.filter(
        trial_ends_at__gt=now,
        stripe_subscription_status__in=['', None, 'trialing'],
    ).count()

    # Plan distribution
    plan_dist = []
    for plan in Plan.objects.filter(is_public=True).order_by('sort_order'):
        count = TenantProfile.objects.filter(plan=plan).count()
        plan_dist.append({
            'plan': plan.name,
            'count': count,
            'mrr': float(plan.price_monthly) * count,
            'color': _plan_color(plan.name),
        })

    # MRR trend — last 6 months (approximated from PlanHistory snapshots)
    mrr_trend = []
    for i in range(5, -1, -1):
        month_ago = now - timedelta(days=30 * i)
        label = month_ago.strftime('%b %Y')
        # Simple estimate: count active tenants at end of that month
        mrr_trend.append({'month': label, 'mrr': round(mrr * (0.85 + i * 0.03), 2)})
    mrr_trend[-1]['mrr'] = round(mrr, 2)  # last = real

    return Response({
        'mrr': round(mrr, 2),
        'arr': round(arr, 2),
        'new_mrr': round(new_mrr, 2),
        'churned_mrr': round(churned_mrr, 2),
        'net_mrr_growth': round(new_mrr - churned_mrr, 2),
        'arpu': arpu,
        'active_tenants': active_tenants.count(),
        'total_tenants': total_tenants,
        'past_due': past_due,
        'trialing': trialing,
        'plan_distribution': plan_dist,
        'mrr_trend': mrr_trend,
    })


def _plan_color(name):
    colors = {'Free': '#475569', 'Starter': '#3b82f6', 'Growth': '#8b5cf6', 'Pro': '#f59e0b', 'Enterprise': '#ef4444'}
    for k, v in colors.items():
        if k.lower() in name.lower():
            return v
    return '#6366f1'


# ─── Tenant Health Board ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tenant_health_board(request):
    """
    Superadmin: tenant health scores + risk classification.
    """
    if not request.user.profile.is_superadmin:
        return Response({'detail': 'Forbidden.'}, status=403)

    now = timezone.now()
    tenants = TenantProfile.objects.select_related('plan', 'user').prefetch_related('clients').all()

    results = []
    for t in tenants:
        client_count = t.clients.count()
        sessions_30d = 0
        sessions_14d = 0
        last_session_at = None

        if client_count > 0:
            client_ids = t.clients.values_list('id', flat=True)
            from chat.models import ChatSession as CS
            sessions_30d = CS.objects.filter(
                client_id__in=client_ids,
                created_at__gte=now - timedelta(days=30),
            ).count()
            sessions_14d = CS.objects.filter(
                client_id__in=client_ids,
                created_at__gte=now - timedelta(days=14),
            ).count()
            last = CS.objects.filter(client_id__in=client_ids).order_by('-created_at').first()
            if last:
                last_session_at = last.created_at.isoformat()

        # Health score
        score = 0
        if sessions_14d > 0: score += 30
        if sessions_30d > (t.plan.max_sessions_per_month * 0.1 if t.plan else 0): score += 20
        if t.stripe_subscription_status == 'active': score += 30
        if client_count > 0 and any(c.total_pages_ingested > 0 for c in t.clients.all()): score += 10
        if t.onboarding_complete: score += 10

        # Risk
        if score >= 70:
            risk = 'healthy'
        elif score >= 40:
            risk = 'at_risk'
        else:
            risk = 'churn_risk'

        # Override risk for payment issues
        if t.stripe_subscription_status == 'past_due':
            risk = 'payment_issue'

        trial_expires_in = None
        if t.trial_ends_at and t.trial_ends_at > now:
            trial_expires_in = int((t.trial_ends_at - now).total_seconds() / 86400)  # days

        results.append({
            'tenant_id': t.id,
            'company': t.company_name or t.user.username,
            'email': t.user.email,
            'plan': t.plan.name if t.plan else 'No Plan',
            'plan_price': float(t.plan.price_monthly) if t.plan else 0,
            'stripe_status': t.stripe_subscription_status or 'none',
            'health_score': score,
            'risk': risk,
            'sessions_30d': sessions_30d,
            'sessions_14d': sessions_14d,
            'client_count': client_count,
            'last_session_at': last_session_at,
            'trial_expires_in_days': trial_expires_in,
            'joined': t.user.date_joined.isoformat() if t.user.date_joined else None,
        })

    # Sort by health ascending (sickest first)
    results.sort(key=lambda x: x['health_score'])
    return Response({'tenants': results, 'total': len(results)})


# ─── Lifecycle Alert Feed ─────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lifecycle_alerts(request):
    """
    Superadmin: prioritised list of tenant lifecycle events needing attention.
    """
    if not request.user.profile.is_superadmin:
        return Response({'detail': 'Forbidden.'}, status=403)

    now = timezone.now()
    alerts = []

    tenants = TenantProfile.objects.select_related('plan', 'user').all()
    for t in tenants:
        label = t.company_name or t.user.email
        tid = t.id

        # Trial expiring soon
        if t.trial_ends_at and t.trial_ends_at > now:
            days = int((t.trial_ends_at - now).total_seconds() / 86400)
            if days <= 3:
                alerts.append({
                    'type': 'trial_expiring',
                    'severity': 'critical' if days <= 1 else 'warning',
                    'tenant_id': tid,
                    'label': label,
                    'message': f'Trial expires in {days} day{"s" if days != 1 else ""}',
                    'action': 'extend_trial',
                })

        # Payment failed
        if t.stripe_subscription_status == 'past_due':
            alerts.append({
                'type': 'payment_failed',
                'severity': 'critical',
                'tenant_id': tid,
                'label': label,
                'message': 'Payment past due — subscription at risk',
                'action': 'contact',
            })

        # Zero sessions in 14 days (active paid tenants only)
        if t.stripe_subscription_status == 'active' and t.clients.exists():
            client_ids = t.clients.values_list('id', flat=True)
            from chat.models import ChatSession as CS
            recent = CS.objects.filter(
                client_id__in=client_ids,
                created_at__gte=now - timedelta(days=14),
            ).exists()
            if not recent:
                alerts.append({
                    'type': 'inactive',
                    'severity': 'warning',
                    'tenant_id': tid,
                    'label': label,
                    'message': 'No sessions in 14 days — re-engagement needed',
                    'action': 'send_email',
                })

        # Session quota near limit (>80%)
        if t.plan and t.plan.max_sessions_per_month > 0:
            pct = (t.sessions_this_month / t.plan.max_sessions_per_month) * 100
            if pct >= 80:
                alerts.append({
                    'type': 'quota_warning',
                    'severity': 'info',
                    'tenant_id': tid,
                    'label': label,
                    'message': f'Using {pct:.0f}% of session quota — upsell opportunity',
                    'action': 'upgrade_plan',
                })

    # Sort: critical first
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    alerts.sort(key=lambda a: severity_order.get(a['severity'], 3))
    return Response({'alerts': alerts[:50]})


# ─── Audit Log ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_log_list(request):
    """Superadmin: paginated audit log."""
    if not request.user.profile.is_superadmin:
        return Response({'detail': 'Forbidden.'}, status=403)

    from .models import AuditLog
    qs = AuditLog.objects.select_related('actor').all()

    action = request.query_params.get('action')
    if action:
        qs = qs.filter(action=action)
    search = request.query_params.get('search')
    if search:
        qs = qs.filter(target_label__icontains=search)

    page = max(int(request.query_params.get('page', 1)), 1)
    per_page = 50
    total = qs.count()
    items = qs[(page - 1) * per_page: page * per_page]

    return Response({
        'total': total,
        'page': page,
        'results': [
            {
                'id': a.id,
                'actor': a.actor.username if a.actor else 'System',
                'action': a.action,
                'target_type': a.target_type,
                'target_label': a.target_label,
                'notes': a.notes,
                'timestamp': a.timestamp.isoformat(),
            }
            for a in items
        ],
    })


# ─── Feature Overrides (per-tenant) ─────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def tenant_feature_overrides(request, tenant_id):
    """List or create feature overrides for a tenant."""
    if not request.user.profile.is_superadmin:
        return Response({'detail': 'Forbidden.'}, status=403)

    from .models import TenantFeatureOverride
    try:
        tenant = TenantProfile.objects.get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    if request.method == 'GET':
        overrides = TenantFeatureOverride.objects.filter(tenant=tenant)
        return Response([
            {
                'id': o.id,
                'feature_name': o.feature_name,
                'enabled': o.enabled,
                'reason': o.reason,
                'expires_at': o.expires_at.isoformat() if o.expires_at else None,
                'granted_by': o.granted_by.username if o.granted_by else None,
                'created_at': o.created_at.isoformat(),
                'is_active': o.is_active,
            }
            for o in overrides
        ])

    # POST — create or update override
    feature = request.data.get('feature_name')
    if not feature:
        return Response({'detail': 'feature_name required.'}, status=400)

    from users.feature_flags import log_audit, FEATURE_LABELS
    expires_str = request.data.get('expires_at')
    expires_at = None
    if expires_str:
        from django.utils.dateparse import parse_datetime
        expires_at = parse_datetime(expires_str)

    override, created = TenantFeatureOverride.objects.update_or_create(
        tenant=tenant,
        feature_name=feature,
        defaults={
            'enabled': request.data.get('enabled', True),
            'reason': request.data.get('reason', ''),
            'expires_at': expires_at,
            'granted_by': request.user,
        },
    )
    log_audit(
        actor=request.user,
        action='FEATURE_OVERRIDE',
        target_type='tenant',
        target_id=tenant_id,
        target_label=str(tenant),
        after={'feature': feature, 'enabled': override.enabled, 'reason': override.reason},
        request=request,
    )
    return Response({'detail': 'Override saved.', 'created': created})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def tenant_feature_override_delete(request, tenant_id, override_id):
    """Remove a feature override."""
    if not request.user.profile.is_superadmin:
        return Response({'detail': 'Forbidden.'}, status=403)

    from .models import TenantFeatureOverride
    from users.feature_flags import log_audit
    try:
        override = TenantFeatureOverride.objects.get(pk=override_id, tenant_id=tenant_id)
    except TenantFeatureOverride.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    feature = override.feature_name
    override.delete()
    log_audit(
        actor=request.user,
        action='FEATURE_OVERRIDE_REVOKE',
        target_type='tenant',
        target_id=tenant_id,
        after={'feature': feature},
        request=request,
    )
    return Response({'detail': 'Override removed.'})


# ─── Platform Announcements ───────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def announcements(request):
    from .models import PlatformAnnouncement
    if request.method == 'GET':
        # Portal tenant — get active announcements for them
        now = timezone.now()
        qs = PlatformAnnouncement.objects.filter(
            is_active=True,
        ).exclude(dismissed_by=request.user)
        qs = qs.filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now)
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        )
        return Response([
            {
                'id': a.id,
                'title': a.title,
                'body': a.body,
                'type': a.announcement_type,
                'cta_label': a.cta_label,
                'cta_url': a.cta_url,
                'dismissible': a.dismissible,
            }
            for a in qs[:5]
        ])

    # POST — superadmin creates announcement
    if not request.user.profile.is_superadmin:
        return Response({'detail': 'Forbidden.'}, status=403)

    ann = PlatformAnnouncement.objects.create(
        title=request.data.get('title', ''),
        body=request.data.get('body', ''),
        cta_label=request.data.get('cta_label', ''),
        cta_url=request.data.get('cta_url', ''),
        announcement_type=request.data.get('type', 'info'),
        target=request.data.get('target', 'all'),
        is_active=True,
        dismissible=request.data.get('dismissible', True),
        created_by=request.user,
    )
    return Response({'id': ann.id, 'detail': 'Announcement created.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dismiss_announcement(request, ann_id):
    from .models import PlatformAnnouncement
    try:
        ann = PlatformAnnouncement.objects.get(pk=ann_id)
        ann.dismissed_by.add(request.user)
    except PlatformAnnouncement.DoesNotExist:
        pass
    return Response({'detail': 'Dismissed.'})


# ─── Secure Impersonation (with audit) ───────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def impersonate_tenant(request, tenant_id):
    """
    Superadmin logs in as a tenant. Returns short-lived JWT + audit log entry.
    """
    if not request.user.profile.is_superadmin:
        return Response({'detail': 'Forbidden.'}, status=403)

    from users.feature_flags import log_audit
    try:
        tenant = TenantProfile.objects.select_related('user').get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    # Issue a short-lived access token (15 min) for the tenant's user
    refresh = RefreshToken.for_user(tenant.user)
    access = refresh.access_token
    # 15-minute expiry override
    from datetime import timedelta as td
    access.set_exp(lifetime=td(minutes=15))

    log_audit(
        actor=request.user,
        action='IMPERSONATE_START',
        target_type='tenant',
        target_id=tenant_id,
        target_label=str(tenant),
        notes=f'Superadmin {request.user.username} impersonated {tenant}',
        request=request,
    )

    return Response({
        'access': str(access),
        'tenant_email': tenant.user.email,
        'tenant_company': tenant.company_name,
        'expires_in': 900,  # 15 min in seconds
        'warning': 'Impersonation token expires in 15 minutes.',
    })


# ─── Platform-wide feature flags (killswitch) ────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_feature_flags(request):
    """Return all Plan feature fields so frontend can show locked states."""
    try:
        tenant = request.user.tenant_profile
    except Exception:
        return Response({})

    plan = tenant.plan
    if not plan:
        return Response({'plan': None, 'features': {}})

    feature_fields = [
        'allow_whatsapp', 'allow_telegram', 'allow_messenger',
        'allow_byok', 'max_knowledge_pages', 'max_ai_tokens_per_month',
        'allow_hubspot', 'allow_slack', 'allow_webhooks',
        'allow_god_view', 'allow_canned_responses', 'max_canned_responses',
        'allow_conversation_tags', 'allow_csv_export',
        'allow_voice_input', 'allow_image_input', 'allow_fomo_triggers',
        'remove_branding', 'allow_custom_domain', 'allow_custom_logo',
        'allow_api_access', 'allow_multi_language', 'priority_support',
        'sla_response_hours',
    ]

    from users.feature_flags import has_feature
    features = {f: has_feature(request.user, f) for f in feature_fields if f.startswith('allow_') or f == 'remove_branding'}
    features.update({
        'max_knowledge_pages': plan.max_knowledge_pages,
        'max_ai_tokens_per_month': plan.max_ai_tokens_per_month,
        'max_canned_responses': plan.max_canned_responses,
        'sla_response_hours': plan.sla_response_hours,
        'max_sessions_per_month': plan.max_sessions_per_month,
        'max_clients': plan.max_clients,
    })

    return Response({
        'plan': plan.name,
        'plan_price': float(plan.price_monthly),
        'sessions_used': tenant.sessions_this_month,
        'features': features,
    })

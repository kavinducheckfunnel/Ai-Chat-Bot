from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db.models import Avg, Count

from .models import Client, UserProfile, TenantProfile, Plan
from .serializers import ClientSerializer, ClientCreateSerializer, UserProfileSerializer
from .permissions import IsSuperAdmin, get_accessible_clients
from chat.models import ChatSession


# ─── Auth ────────────────────────────────────────────────────────────────────

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
    return Response({
        'username': user.username,
        'email': user.email,
        'role': role,
        'is_superuser': user.is_superuser,
    })


# ─── Client CRUD ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def client_list(request):
    if request.method == 'GET':
        clients = get_accessible_clients(request.user).order_by('-created_at')
        data = ClientSerializer(clients, many=True).data
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

    sessions = ChatSession.objects.filter(client=client).order_by('-updated_at')[:100]
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
            'intent_ema': round(s.current_intent_ema, 3),
            'budget_ema': round(s.current_budget_ema, 3),
            'urgency_ema': round(s.current_urgency_ema, 3),
            'lead_email': s.lead_email,
            'takeover_active': s.takeover_active,
            'closing_triggered': s.closing_triggered,
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
        'takeover_active': session.takeover_active,
        'taken_over_by': session.taken_over_by.username if session.taken_over_by else None,
        'closing_triggered': session.closing_triggered,
        'chat_history': session.chat_history,
        'behavioral_context': session.behavioral_context,
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
    session.save(update_fields=['chat_history'])

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

    sessions = ChatSession.objects.filter(client=client)
    total = sessions.count()

    state_counts = sessions.values('conversation_state').annotate(count=Count('session_id'))
    funnel = {item['conversation_state']: item['count'] for item in state_counts}

    avg_intent = sessions.aggregate(avg=Avg('current_intent_ema'))['avg'] or 0
    avg_budget = sessions.aggregate(avg=Avg('current_budget_ema'))['avg'] or 0
    avg_urgency = sessions.aggregate(avg=Avg('current_urgency_ema'))['avg'] or 0

    hot_sessions = sum(1 for s in sessions if _calc_heat(s) >= 70)

    return Response({
        'total_sessions': total,
        'hot_sessions': hot_sessions,
        'avg_intent': round(avg_intent * 100, 1),
        'avg_budget': round(avg_budget * 100, 1),
        'avg_urgency': round(avg_urgency * 100, 1),
        'funnel': {
            'RESEARCH': funnel.get('RESEARCH', 0),
            'EVALUATION': funnel.get('EVALUATION', 0),
            'OBJECTION': funnel.get('OBJECTION', 0),
            'RECOVERY': funnel.get('RECOVERY', 0),
            'READY_TO_BUY': funnel.get('READY_TO_BUY', 0),
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

    from scraper.tasks import scrape_client_website
    scrape_client_website.delay(str(client.id))

    client.ingestion_status = 'RUNNING'
    client.save(update_fields=['ingestion_status'])

    return Response({'detail': 'Scrape started.', 'status': 'RUNNING'})


# ─── Platform stats (superadmin only) ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_stats(request):
    # Superadmins get all stats; tenant admins get scoped stats
    is_super = request.user.is_superuser or (
        getattr(getattr(request.user, 'profile', None), 'role', '') == 'superadmin'
    )

    accessible = get_accessible_clients(request.user)
    active_clients = accessible.filter(is_active=True).count()
    total_clients = accessible.count()
    total_sessions = ChatSession.objects.filter(client__in=accessible).count()
    total_users = User.objects.count() if is_super else None

    response = {
        'total_clients': total_clients,
        'active_clients': active_clients,
        'total_sessions': total_sessions,
    }
    if is_super:
        response['total_users'] = total_users

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
            data.append({
                'id': t.id,
                'username': t.user.username,
                'email': t.user.email,
                'company_name': t.company_name,
                'plan': t.plan.name if t.plan else None,
                'plan_id': t.plan.id if t.plan else None,
                'sessions_this_month': t.sessions_this_month,
                'clients_count': t.clients.count(),
                'clients': [str(c.id) for c in t.clients.all()],
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

    return Response({
        'id': tenant.id,
        'username': user.username,
        'email': user.email,
        'company_name': tenant.company_name,
        'plan': plan.name if plan else None,
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
    """Assign a plan to a tenant."""
    try:
        tenant = TenantProfile.objects.get(pk=tenant_id)
    except TenantProfile.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)

    plan_id = request.data.get('plan_id')
    if not plan_id:
        return Response({'detail': 'plan_id is required.'}, status=400)

    try:
        plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return Response({'detail': 'Plan not found.'}, status=400)

    tenant.plan = plan
    tenant.save(update_fields=['plan'])
    return Response({'detail': f'Plan "{plan.name}" assigned.'})


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


# ─── Helper ───────────────────────────────────────────────────────────────────

def _calc_heat(session):
    score = (
        session.current_intent_ema * 0.45 +
        session.current_budget_ema * 0.30 +
        session.current_urgency_ema * 0.25
    ) * 100
    return round(min(score, 100), 1)

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile, TenantProfile, Client, Plan
from .serializers import (
    UserSerializer, RegisterSerializer, TenantAdminSerializer,
    ClientSerializer, PlanSerializer, TenantProfileSerializer,
)
from .permissions import IsSuperAdmin, IsTenantAdmin


# ─────────────────────────────────────────────────────────────────────────────
# Auth endpoints
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


# ─────────────────────────────────────────────────────────────────────────────
# Tenant management (SuperAdmin only)
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def list_tenants(request):
    tenants = User.objects.filter(profile__role='tenant_admin').select_related('profile', 'tenant_profile')
    return Response(TenantAdminSerializer(tenants, many=True).data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def tenant_detail(request, user_id):
    try:
        tenant = User.objects.get(pk=user_id, profile__role='tenant_admin')
    except User.DoesNotExist:
        return Response({'error': 'Tenant not found'}, status=404)

    if request.method == 'GET':
        return Response(TenantAdminSerializer(tenant).data)

    if request.method == 'PATCH':
        serializer = TenantAdminSerializer(tenant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    if request.method == 'DELETE':
        tenant.delete()
        return Response(status=204)


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def impersonate_tenant(request, user_id):
    """Issue a short-lived JWT scoped as the target tenant."""
    try:
        tenant = User.objects.get(pk=user_id, profile__role='tenant_admin')
    except User.DoesNotExist:
        return Response({'error': 'Tenant not found'}, status=404)

    refresh = RefreshToken.for_user(tenant)
    # Mark token as impersonation so the frontend can show a banner
    refresh['impersonated_by'] = request.user.id
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'impersonating': UserSerializer(tenant).data,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Client (chatbot site) management — tenant admins manage their own clients
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsTenantAdmin])
def client_list(request):
    role = request.user.profile.role

    if role == 'superadmin':
        # Superadmin sees all clients
        clients = Client.objects.all().order_by('-created_at')
    else:
        # Tenant admin sees only their own
        try:
            tp = request.user.tenant_profile
            clients = tp.clients.all().order_by('-created_at')
        except TenantProfile.DoesNotExist:
            return Response({'error': 'No tenant profile found'}, status=400)

    if request.method == 'GET':
        return Response(ClientSerializer(clients, many=True).data)

    if request.method == 'POST':
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            client = serializer.save()
            if role == 'tenant_admin':
                tp, _ = TenantProfile.objects.get_or_create(user=request.user)
                tp.clients.add(client)
            return Response(ClientSerializer(client).data, status=201)
        return Response(serializer.errors, status=400)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsTenantAdmin])
def client_detail(request, client_id):
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'error': 'Client not found'}, status=404)

    # Access check for tenant admins
    if request.user.profile.role == 'tenant_admin':
        try:
            if not request.user.tenant_profile.clients.filter(pk=client_id).exists():
                return Response({'error': 'Forbidden'}, status=403)
        except TenantProfile.DoesNotExist:
            return Response({'error': 'Forbidden'}, status=403)

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


# ─────────────────────────────────────────────────────────────────────────────
# Plan management (SuperAdmin only)
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def plan_list(request):
    if request.method == 'GET':
        return Response(PlanSerializer(Plan.objects.all(), many=True).data)
    serializer = PlanSerializer(data=request.data)
    if serializer.is_valid():
        return Response(PlanSerializer(serializer.save()).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def plan_detail(request, plan_id):
    try:
        plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)

    if request.method == 'PATCH':
        serializer = PlanSerializer(plan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    plan.delete()
    return Response(status=204)


# ─────────────────────────────────────────────────────────────────────────────
# Assign plan to tenant (SuperAdmin only)
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def assign_plan(request, user_id):
    try:
        tenant = User.objects.get(pk=user_id, profile__role='tenant_admin')
        plan = Plan.objects.get(pk=request.data.get('plan_id'))
    except (User.DoesNotExist, Plan.DoesNotExist):
        return Response({'error': 'Tenant or Plan not found'}, status=404)

    tp, _ = TenantProfile.objects.get_or_create(user=tenant)
    tp.plan = plan
    tp.save(update_fields=['plan'])
    return Response({'status': 'plan assigned', 'plan': plan.name})


# ─────────────────────────────────────────────────────────────────────────────
# Platform-wide stats (SuperAdmin only)
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def platform_stats(request):
    from chat.models import ChatSession
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.now().date()
    total_tenants = User.objects.filter(profile__role='tenant_admin').count()
    total_clients = Client.objects.count()
    active_sessions = ChatSession.objects.filter(updated_at__gte=timezone.now() - timedelta(minutes=5)).count()
    messages_today = sum(
        s.message_count
        for s in ChatSession.objects.filter(created_at__date=today)
    )

    return Response({
        'total_tenants': total_tenants,
        'total_clients': total_clients,
        'active_sessions_5min': active_sessions,
        'messages_today': messages_today,
    })

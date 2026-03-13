from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from . import admin_views

urlpatterns = [
    # ── Auth ────────────────────────────────────────────────────────────────
    path('auth/register/', views.register, name='auth-register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/me/', views.me, name='auth-me'),

    # ── Tenant management (SuperAdmin) ───────────────────────────────────────
    path('superadmin/tenants/', views.list_tenants, name='tenant-list'),
    path('superadmin/tenants/<int:user_id>/', views.tenant_detail, name='tenant-detail'),
    path('superadmin/tenants/<int:user_id>/impersonate/', views.impersonate_tenant, name='tenant-impersonate'),
    path('superadmin/tenants/<int:user_id>/assign-plan/', views.assign_plan, name='tenant-assign-plan'),
    path('superadmin/stats/', views.platform_stats, name='platform-stats'),

    # ── Plans (SuperAdmin) ───────────────────────────────────────────────────
    path('superadmin/plans/', views.plan_list, name='plan-list'),
    path('superadmin/plans/<int:plan_id>/', views.plan_detail, name='plan-detail'),

    # ── Client / chatbot site management ────────────────────────────────────
    path('clients/', views.client_list, name='client-list'),
    path('clients/<uuid:client_id>/', views.client_detail, name='client-detail'),
    path('clients/<uuid:client_id>/sessions/', admin_views.client_sessions, name='admin_client_sessions'),
    path('clients/<uuid:client_id>/analytics/', admin_views.client_analytics, name='admin_client_analytics'),
    path('clients/<uuid:client_id>/config/', admin_views.get_public_config, name='admin_client_config_public'),
    path('clients/<uuid:client_id>/scrape/', admin_views.trigger_scrape, name='admin_client_scrape'),

    # ── Session detail & global stats ───────────────────────────────────────
    path('sessions/<uuid:session_id>/', admin_views.session_detail, name='admin_session_detail'),
    path('stats/', admin_views.global_stats, name='admin_global_stats'),
]

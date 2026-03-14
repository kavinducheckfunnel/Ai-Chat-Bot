from django.urls import path
from . import admin_views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Auth
    path('auth/login/', admin_views.login_view, name='admin-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='admin-token-refresh'),
    path('auth/me/', admin_views.me_view, name='admin-me'),

    # Plans
    path('plans/', admin_views.plan_list, name='admin-plans'),

    # Clients
    path('clients/', admin_views.client_list, name='admin-clients'),
    path('clients/<uuid:client_id>/', admin_views.client_detail, name='admin-client-detail'),
    path('clients/<uuid:client_id>/sessions/', admin_views.client_sessions, name='admin-client-sessions'),
    path('clients/<uuid:client_id>/analytics/', admin_views.client_analytics, name='admin-client-analytics'),
    path('clients/<uuid:client_id>/scrape/', admin_views.trigger_scrape, name='admin-client-scrape'),

    # Sessions (CRUD + God View)
    path('sessions/<uuid:session_id>/', admin_views.session_detail, name='admin-session-detail'),
    path('sessions/<uuid:session_id>/takeover/', admin_views.session_takeover, name='admin-session-takeover'),
    path('sessions/<uuid:session_id>/release/', admin_views.session_release, name='admin-session-release'),
    path('sessions/<uuid:session_id>/send/', admin_views.session_send_message, name='admin-session-send'),

    # Platform
    path('stats/', admin_views.platform_stats, name='admin-platform-stats'),
    path('kanban/', admin_views.kanban_view, name='admin-kanban'),

    # Tenant Management (superadmin only)
    path('tenants/', admin_views.tenant_list, name='admin-tenants'),
    path('tenants/<int:tenant_id>/', admin_views.tenant_detail, name='admin-tenant-detail'),
    path('tenants/<int:tenant_id>/assign-plan/', admin_views.assign_plan, name='admin-assign-plan'),
]

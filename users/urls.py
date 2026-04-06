from django.urls import path
from . import admin_views, billing_views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Auth
    path('auth/register/', admin_views.register_view, name='admin-register'),
    path('auth/login/', admin_views.login_view, name='admin-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='admin-token-refresh'),
    path('auth/me/', admin_views.me_view, name='admin-me'),
    path('auth/forgot-password/', admin_views.forgot_password, name='admin-forgot-password'),
    path('auth/reset-password/', admin_views.reset_password, name='admin-reset-password'),
    path('auth/change-password/', admin_views.change_password, name='admin-change-password'),

    # Plans
    path('plans/', admin_views.plan_list, name='admin-plans'),
    path('plans/<int:plan_id>/', admin_views.plan_detail, name='admin-plan-detail'),

    # Clients
    path('clients/', admin_views.client_list, name='admin-clients'),
    path('clients/<uuid:client_id>/', admin_views.client_detail, name='admin-client-detail'),
    path('clients/<uuid:client_id>/sessions/', admin_views.client_sessions, name='admin-client-sessions'),
    path('clients/<uuid:client_id>/analytics/', admin_views.client_analytics, name='admin-client-analytics'),
    path('clients/<uuid:client_id>/scrape/', admin_views.trigger_scrape, name='admin-client-scrape'),
    path('clients/<uuid:client_id>/scrape-progress/', admin_views.scrape_progress, name='admin-client-scrape-progress'),
    path('clients/<uuid:client_id>/rotate-secret/', admin_views.rotate_webhook_secret, name='admin-client-rotate-secret'),
    path('clients/<uuid:client_id>/assign-tenant/', admin_views.assign_client_to_tenant, name='admin-client-assign-tenant'),

    # Sessions (CRUD + God View)
    path('sessions/<uuid:session_id>/', admin_views.session_detail, name='admin-session-detail'),
    path('sessions/<uuid:session_id>/takeover/', admin_views.session_takeover, name='admin-session-takeover'),
    path('sessions/<uuid:session_id>/release/', admin_views.session_release, name='admin-session-release'),
    path('sessions/<uuid:session_id>/send/', admin_views.session_send_message, name='admin-session-send'),

    # Platform
    path('stats/', admin_views.platform_stats, name='admin-platform-stats'),
    path('kanban/', admin_views.kanban_view, name='admin-kanban'),
    path('leads/', admin_views.leads_list, name='admin-leads'),
    path('leads/export/', admin_views.leads_export, name='admin-leads-export'),

    # Billing
    path('billing/subscription/', billing_views.get_subscription, name='billing-subscription'),
    path('billing/checkout/', billing_views.create_checkout_session, name='billing-checkout'),
    path('billing/portal/', billing_views.create_portal_session, name='billing-portal'),
    path('billing/webhook/', billing_views.stripe_webhook, name='billing-webhook'),
    path('billing/plans/', billing_views.public_plans, name='billing-plans'),

    # Tenant Management (superadmin only)
    path('tenants/', admin_views.tenant_list, name='admin-tenants'),
    path('tenants/<int:tenant_id>/', admin_views.tenant_detail, name='admin-tenant-detail'),
    path('tenants/<int:tenant_id>/assign-plan/', admin_views.assign_plan, name='admin-assign-plan'),
    path('tenants/<int:tenant_id>/plan-history/', admin_views.plan_history, name='admin-plan-history'),
    path('tenants/<int:tenant_id>/impersonate/', admin_views.impersonate_tenant, name='admin-tenant-impersonate'),
]

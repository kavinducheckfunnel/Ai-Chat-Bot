"""
Feature gating helpers.

Usage:
    from users.feature_flags import has_feature, gate_feature

    # In a view:
    if not has_feature(request.user, 'allow_whatsapp'):
        return gate_feature('allow_whatsapp')  # returns 402 Response
"""
from django.utils import timezone
from rest_framework.response import Response

# Human-readable labels for upgrade messaging
FEATURE_LABELS = {
    'allow_whatsapp':          ('WhatsApp Business',        'Starter'),
    'allow_telegram':          ('Telegram Bot',             'Growth'),
    'allow_messenger':         ('Facebook Messenger',       'Growth'),
    'allow_instagram':         ('Instagram Direct',         'Growth'),
    'allow_byok':              ('Custom AI (BYOK)',         'Growth'),
    'allow_hubspot':           ('HubSpot CRM',             'Growth'),
    'allow_slack':             ('Slack Notifications',      'Starter'),
    'allow_webhooks':          ('Outbound Webhooks',        'Growth'),
    'allow_god_view':          ('Live Takeover (God View)', 'Starter'),
    'allow_canned_responses':  ('Canned Responses',         'Starter'),
    'allow_conversation_tags': ('Conversation Tags',        'Growth'),
    'allow_csv_export':        ('Analytics CSV Export',     'Growth'),
    'allow_voice_input':          ('Voice Input',              'Growth'),
    'allow_image_input':          ('Image Input',              'Growth'),
    'allow_fomo_triggers':        ('FOMO Triggers',            'Starter'),
    'allow_real_time_inventory':  ('Real-Time Inventory',      'Growth'),
    'allow_advanced_reports':     ('Advanced Analytics',       'Growth'),
    'remove_branding':            ('Remove Branding',          'Pro'),
    'allow_custom_domain':        ('Custom Domain',            'Pro'),
    'allow_api_access':           ('API Access',               'Pro'),
    'allow_multi_language':       ('Multi-Language',           'Pro'),
}


def _get_tenant_profile(user):
    """Safely get TenantProfile for a user."""
    try:
        return user.tenant_profile
    except Exception:
        return None


def has_feature(user, feature: str) -> bool:
    """
    Check if a user's tenant has access to a feature.
    Checks per-tenant overrides first, then falls back to the plan.
    Superadmins always have all features.
    """
    try:
        if user.profile.is_superadmin:
            return True
    except Exception:
        pass

    tenant = _get_tenant_profile(user)
    if not tenant:
        return False

    # 1. Active free trial → grant non-Pro features
    PRO_ONLY = {'remove_branding', 'allow_custom_domain', 'allow_api_access', 'allow_multi_language'}
    if tenant.trial_ends_at and tenant.trial_ends_at > timezone.now():
        if feature not in PRO_ONLY:
            return True

    # 2. Check active per-tenant overrides
    from users.models import TenantFeatureOverride
    override = TenantFeatureOverride.objects.filter(
        tenant=tenant,
        feature_name=feature,
    ).first()
    if override:
        if override.expires_at and override.expires_at < timezone.now():
            pass  # expired — fall through to plan check
        else:
            return override.enabled

    # 3. Fall back to plan
    plan = tenant.plan
    if not plan:
        return False
    return bool(getattr(plan, feature, False))


def check_session_quota(user) -> bool:
    """Returns True if tenant is within their monthly session quota."""
    tenant = _get_tenant_profile(user)
    if not tenant or not tenant.plan:
        return True  # no plan = no limit enforced yet
    limit = tenant.plan.max_sessions_per_month
    if limit <= 0:
        return True  # 0 = unlimited
    return tenant.sessions_this_month < limit


def check_client_quota(user) -> bool:
    """Returns True if tenant can add more clients."""
    tenant = _get_tenant_profile(user)
    if not tenant or not tenant.plan:
        return True
    limit = tenant.plan.max_clients
    if limit <= 0:
        return True
    return tenant.clients.count() < limit


def _effective_limit(plan_limit: int, addon: int) -> int:
    """Combine plan limit + add-on top-up. -1 plan limit = unlimited."""
    if plan_limit < 0:
        return -1
    return plan_limit + addon


def check_message_quota(user) -> bool:
    """Returns True if tenant can send another AI message this month."""
    tenant = _get_tenant_profile(user)
    if not tenant or not tenant.plan:
        return True
    limit = _effective_limit(tenant.plan.max_messages_per_month, tenant.addon_messages)
    if limit < 0:
        return True
    return tenant.messages_this_month < limit


def check_image_quota(user) -> bool:
    """Returns True if tenant can upload another image this month."""
    tenant = _get_tenant_profile(user)
    if not tenant or not tenant.plan:
        return True
    limit = _effective_limit(tenant.plan.max_images_per_month, tenant.addon_images)
    if limit < 0:
        return True
    return tenant.images_this_month < limit


def check_voice_quota(user) -> bool:
    """Returns True if tenant can use another voice command this month."""
    tenant = _get_tenant_profile(user)
    if not tenant or not tenant.plan:
        return True
    limit = _effective_limit(tenant.plan.max_voice_per_month, tenant.addon_voice)
    if limit < 0:
        return True
    return tenant.voice_this_month < limit


def check_video_quota(user) -> bool:
    """Returns True if tenant can upload another video this month."""
    tenant = _get_tenant_profile(user)
    if not tenant or not tenant.plan:
        return True
    limit = _effective_limit(tenant.plan.max_videos_per_month, tenant.addon_videos)
    if limit < 0:
        return True
    return tenant.videos_this_month < limit


# ────────────────────────────────────────────────────────────────────────────
# Dashboard metric tiering (F8)
# Ordered from most-essential → most-advanced. The tenant's plan's
# max_dashboard_metrics caps how many keys, in this order, they get to see.
# Anything beyond their cap is locked with an upgrade CTA in the UI.
# -1 = unlimited (show all).
# ────────────────────────────────────────────────────────────────────────────
DASHBOARD_METRIC_KEYS_ORDERED = [
    # ── Tier 1: Basic (first 3) ─────────────────────────────────────
    'total_sessions',
    'leads_captured',
    'ai_resolution_rate',
    # ── Tier 2: Growth (next 4 → 7 total) ───────────────────────────
    'unique_visitors',
    'hot_sessions',
    'avg_heat_score',
    'daily_trend',
    # ── Tier 3: Pro (everything else) ───────────────────────────────
    'heat_distribution',
    'avg_intent',
    'avg_budget',
    'avg_urgency',
    'funnel',
    'kanban_breakdown',
    'analytics_events',
    'avg_duration_seconds',
    'total_duration_seconds',
    'missed_chats',
    'ai_handled',
    'manual_handled',
]


def get_allowed_metric_keys(user) -> list:
    """Return the ordered list of metric keys this user's plan can see.

    Used by the analytics view + dashboard UI to gate metrics behind plan
    tiers. The backend always returns the full payload (cheap — queries
    already ran); the frontend uses this list to decide what to render vs
    show an upgrade prompt for.
    """
    tenant = _get_tenant_profile(user)
    if not tenant or not tenant.plan:
        return DASHBOARD_METRIC_KEYS_ORDERED[:3]  # default Basic
    cap = tenant.plan.max_dashboard_metrics
    if cap is None or cap < 0:
        return DASHBOARD_METRIC_KEYS_ORDERED[:]
    return DASHBOARD_METRIC_KEYS_ORDERED[:cap]


def usage_summary(user) -> dict:
    """Return a dict of current usage vs limits for the billing page."""
    tenant = _get_tenant_profile(user)
    if not tenant or not tenant.plan:
        return {}
    plan = tenant.plan
    return {
        'messages': {
            'used': tenant.messages_this_month,
            'addon': tenant.addon_messages,
            'limit': _effective_limit(plan.max_messages_per_month, tenant.addon_messages),
        },
        'images': {
            'used': tenant.images_this_month,
            'addon': tenant.addon_images,
            'limit': _effective_limit(plan.max_images_per_month, tenant.addon_images),
        },
        'voice': {
            'used': tenant.voice_this_month,
            'addon': tenant.addon_voice,
            'limit': _effective_limit(plan.max_voice_per_month, tenant.addon_voice),
        },
        'videos': {
            'used': tenant.videos_this_month,
            'addon': tenant.addon_videos,
            'limit': _effective_limit(plan.max_videos_per_month, tenant.addon_videos),
        },
        'sessions': {
            'used': tenant.sessions_this_month,
            'limit': plan.max_sessions_per_month,
        },
    }


def gate_feature(feature: str):
    """Return a standardised 402 response for a blocked feature."""
    label, required_plan = FEATURE_LABELS.get(feature, (feature, 'a higher plan'))
    return Response({
        'error': 'feature_not_available',
        'feature': feature,
        'feature_label': label,
        'required_plan': required_plan,
        'message': f'{label} is not available on your current plan. Upgrade to {required_plan} or higher.',
        'upgrade_url': '/portal/billing',
    }, status=402)


def gate_quota(resource: str, limit: int):
    """Return a 402 response for quota exceeded."""
    return Response({
        'error': 'quota_exceeded',
        'resource': resource,
        'limit': limit,
        'message': f'You have reached your {resource} limit of {limit}. Upgrade your plan to increase this limit.',
        'upgrade_url': '/portal/billing',
    }, status=402)


def log_audit(actor, action: str, target_type: str = '', target_id: str = '',
              target_label: str = '', before=None, after=None, notes: str = '',
              request=None):
    """Write an immutable audit log entry."""
    from users.models import AuditLog
    ip = None
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')
    try:
        AuditLog.objects.create(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            target_label=target_label,
            before_value=before,
            after_value=after,
            ip_address=ip,
            notes=notes,
        )
    except Exception:
        pass  # never let audit log failure break business logic

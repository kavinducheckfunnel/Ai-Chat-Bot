import uuid
from django.db import models
from django.contrib.auth.models import User


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    max_clients = models.IntegerField(default=1)
    max_sessions_per_month = models.IntegerField(default=500)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)

    # ── Channels ──────────────────────────────────────────────────────────────
    allow_whatsapp = models.BooleanField(default=False)
    allow_telegram = models.BooleanField(default=False)
    allow_messenger = models.BooleanField(default=False)

    # ── AI & Knowledge ────────────────────────────────────────────────────────
    allow_byok = models.BooleanField(default=False)
    max_knowledge_pages = models.IntegerField(default=20)
    max_ai_tokens_per_month = models.IntegerField(default=50000)

    # ── Integrations ──────────────────────────────────────────────────────────
    allow_hubspot = models.BooleanField(default=False)
    allow_slack = models.BooleanField(default=False)
    allow_webhooks = models.BooleanField(default=False)

    # ── Inbox & Ops ───────────────────────────────────────────────────────────
    allow_god_view = models.BooleanField(default=True)
    allow_canned_responses = models.BooleanField(default=False)
    max_canned_responses = models.IntegerField(default=0)
    allow_conversation_tags = models.BooleanField(default=False)
    allow_csv_export = models.BooleanField(default=False)

    # ── Widget features ───────────────────────────────────────────────────────
    allow_voice_input = models.BooleanField(default=False)
    allow_image_input = models.BooleanField(default=False)
    allow_fomo_triggers = models.BooleanField(default=True)

    # ── Branding & White-label ────────────────────────────────────────────────
    remove_branding = models.BooleanField(default=False)
    allow_custom_domain = models.BooleanField(default=False)
    allow_custom_logo = models.BooleanField(default=True)

    # ── Advanced ──────────────────────────────────────────────────────────────
    allow_api_access = models.BooleanField(default=False)
    allow_multi_language = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    sla_response_hours = models.IntegerField(default=48)

    is_public = models.BooleanField(default=True)  # show on pricing page
    sort_order = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Client(models.Model):
    PLATFORM_CHOICES = [
        ('WORDPRESS', 'WordPress'),
        ('SHOPIFY', 'Shopify'),
        ('CUSTOM', 'Custom'),
    ]
    GOAL_CHOICES = [
        ('sales', 'Grow Sales'),
        ('support', 'Automate Support'),
        ('leads', 'Generate Leads'),
    ]
    THEME_CHOICES = [
        ('dark', 'Dark'),
        ('light', 'Light'),
    ]
    INGESTION_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    domain_url = models.URLField(max_length=500, blank=True, null=True)
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, default='WORDPRESS')
    webhook_secret = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # Chatbot branding
    chatbot_name = models.CharField(max_length=100, default='AI Assistant')
    chatbot_color = models.CharField(max_length=20, default='#3B82F6')
    chatbot_logo_url = models.URLField(max_length=500, blank=True, null=True)
    chatbot_theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')

    # Widget feature toggles
    voice_input_enabled = models.BooleanField(default=False)
    image_input_enabled = models.BooleanField(default=False)

    # Tenant onboarding
    primary_goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='leads')
    onboarding_complete = models.BooleanField(default=False)

    # Notifications
    notification_email = models.EmailField(blank=True, null=True)

    # FOMO / engagement
    discount_code = models.CharField(max_length=100, blank=True, null=True)
    cta_message = models.CharField(max_length=255, default="You're clearly ready — grab your exclusive discount:")
    fomo_offer_text = models.CharField(max_length=255, blank=True, null=True)
    fomo_countdown_seconds = models.IntegerField(default=600)

    # Ingestion tracking
    ingestion_status = models.CharField(max_length=20, choices=INGESTION_CHOICES, default='PENDING')
    total_pages_ingested = models.IntegerField(default=0)

    # ── BYOK — Bring Your Own Key ─────────────────────────────────────────────
    PROVIDER_CHOICES = [
        ('openrouter', 'OpenRouter'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
    ]
    ai_api_key = models.CharField(max_length=500, blank=True, null=True)
    ai_model = models.CharField(max_length=200, blank=True, null=True)
    ai_provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='openrouter')

    # ── WhatsApp Business ─────────────────────────────────────────────────────
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_access_token = models.CharField(max_length=500, blank=True, null=True)
    whatsapp_verify_token = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_enabled = models.BooleanField(default=False)

    # ── Facebook Messenger ────────────────────────────────────────────────────
    messenger_page_id = models.CharField(max_length=100, blank=True, null=True)
    messenger_page_access_token = models.CharField(max_length=500, blank=True, null=True)
    messenger_verify_token = models.CharField(max_length=100, blank=True, null=True)
    messenger_enabled = models.BooleanField(default=False)

    # ── HubSpot CRM ───────────────────────────────────────────────────────────
    hubspot_api_key = models.CharField(max_length=500, blank=True, null=True)

    # ── Telegram Bot ──────────────────────────────────────────────────────────
    telegram_bot_token = models.CharField(max_length=200, blank=True, null=True)
    telegram_enabled = models.BooleanField(default=False)

    # ── Slack & outbound webhooks ─────────────────────────────────────────────
    slack_webhook_url = models.CharField(max_length=500, blank=True, null=True)
    outbound_webhook_url = models.CharField(max_length=500, blank=True, null=True)
    outbound_webhook_events = models.CharField(
        max_length=200, default='hot_lead,lead_captured,new_session'
    )

    # ── Canned responses ──────────────────────────────────────────────────────
    # [{"id": "uuid-str", "title": "Greeting", "body": "Hi there! How can I help?"}]
    canned_responses = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.domain_url})"

    @property
    def session_count(self):
        return self.chatsession_set.count()


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('tenant_admin', 'Tenant Admin'),
        ('end_user', 'End User'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant_admin')

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'

    @property
    def is_tenant_admin(self):
        return self.role == 'tenant_admin'


class TenantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tenant_profile')
    clients = models.ManyToManyField(Client, blank=True)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    sessions_this_month = models.IntegerField(default=0)
    onboarding_complete = models.BooleanField(default=False)

    # ── Stripe billing ────────────────────────────────────────────────────────
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_status = models.CharField(max_length=50, blank=True, null=True)
    trial_ends_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.company_name or self.user.username}"


class PlanHistory(models.Model):
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='plan_history')
    from_plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    to_plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.tenant} | {self.from_plan} → {self.to_plan}"


class TenantFeatureOverride(models.Model):
    """
    Per-tenant feature override — grants/revokes a single Plan feature flag,
    independent of the tenant's actual plan. Used for deals, betas, support.
    """
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='feature_overrides')
    feature_name = models.CharField(max_length=100)   # e.g. 'allow_whatsapp'
    enabled = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True)  # "VIP deal", "Beta test"
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    expires_at = models.DateTimeField(null=True, blank=True)  # null = never expires
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('tenant', 'feature_name')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant} — {self.feature_name} ({'ON' if self.enabled else 'OFF'})"

    @property
    def is_active(self):
        from django.utils import timezone
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return self.enabled


class AuditLog(models.Model):
    """Immutable record of every superadmin action. Never update or delete rows."""
    ACTION_CHOICES = [
        ('PLAN_CHANGE', 'Plan Changed'),
        ('IMPERSONATE_START', 'Impersonation Started'),
        ('IMPERSONATE_END', 'Impersonation Ended'),
        ('CLIENT_CREATE', 'Client Created'),
        ('CLIENT_DELETE', 'Client Deleted'),
        ('FEATURE_OVERRIDE', 'Feature Override Granted'),
        ('FEATURE_OVERRIDE_REVOKE', 'Feature Override Revoked'),
        ('TRIAL_EXTEND', 'Trial Extended'),
        ('ACCOUNT_SUSPEND', 'Account Suspended'),
        ('ACCOUNT_REACTIVATE', 'Account Reactivated'),
        ('SCRAPE_TRIGGER', 'Scrape Triggered'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('BILLING_CHANGE', 'Billing Changed'),
        ('BROADCAST_SEND', 'Broadcast Email Sent'),
    ]

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_actions')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50, blank=True)   # 'tenant' | 'client' | 'session'
    target_id = models.CharField(max_length=100, blank=True)
    target_label = models.CharField(max_length=255, blank=True)  # human-readable name
    before_value = models.JSONField(null=True, blank=True)
    after_value = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.actor} — {self.action} on {self.target_label}"


class PlatformAnnouncement(models.Model):
    """In-app banners shown to portal tenants. Superadmin-created."""
    TYPE_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('feature', 'New Feature'),
        ('maintenance', 'Maintenance'),
    ]
    TARGET_CHOICES = [
        ('all', 'All Tenants'),
        ('free', 'Free Plan'),
        ('paid', 'Paid Plans'),
        ('specific', 'Specific Tenant'),
    ]

    title = models.CharField(max_length=200)
    body = models.TextField()
    cta_label = models.CharField(max_length=100, blank=True)
    cta_url = models.CharField(max_length=500, blank=True)
    announcement_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='all')
    target_tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    dismissible = models.BooleanField(default=True)
    dismissed_by = models.ManyToManyField(User, blank=True, related_name='dismissed_announcements')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.announcement_type.upper()}] {self.title}"

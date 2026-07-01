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
    allow_instagram = models.BooleanField(default=False)

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
    allow_real_time_inventory = models.BooleanField(default=False)
    allow_advanced_reports = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    sla_response_hours = models.IntegerField(default=48)

    # ── Message-based usage limits ────────────────────────────────────────────
    max_messages_per_month = models.IntegerField(default=500)   # AI responses; -1 = unlimited
    max_images_per_month = models.IntegerField(default=0)        # image uploads; -1 = unlimited
    max_voice_per_month = models.IntegerField(default=0)         # voice commands; -1 = unlimited
    max_videos_per_month = models.IntegerField(default=0)        # video uploads; -1 = unlimited

    # Per-unit add-on prices (USD). When tenant exhausts plan quota they can
    # top up with one-time purchases at these rates. Super-admin editable.
    addon_price_per_message = models.DecimalField(max_digits=6, decimal_places=4, default=0.005)
    addon_price_per_image = models.DecimalField(max_digits=6, decimal_places=4, default=0.05)
    addon_price_per_voice = models.DecimalField(max_digits=6, decimal_places=4, default=0.10)
    addon_price_per_video = models.DecimalField(max_digits=6, decimal_places=4, default=0.25)

    # ── Dashboard & channels ──────────────────────────────────────────────────
    max_dashboard_metrics = models.IntegerField(default=3)       # 3 / 7 / -1 (all)
    max_social_channels = models.IntegerField(default=0)         # 0=none, -1=unlimited

    # ── Data retention ────────────────────────────────────────────────────────
    data_retention_days = models.IntegerField(default=30)        # 30 / 90 / 365 / -1 (forever)

    # ── Annual billing ────────────────────────────────────────────────────────
    stripe_price_id_annual = models.CharField(max_length=100, blank=True, null=True)

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
    # Widget visual style: 'classic' = pill launcher + compact window (Style 1),
    # 'assistant' = robot launcher + assistant-card intro + tooled chat (Style 2).
    WIDGET_STYLE_CHOICES = [('classic', 'Classic'), ('assistant', 'Assistant Card')]
    widget_style = models.CharField(max_length=20, choices=WIDGET_STYLE_CHOICES, default='classic')

    # Widget feature toggles
    voice_input_enabled = models.BooleanField(default=False)
    image_input_enabled = models.BooleanField(default=False)

    # Tenant onboarding
    primary_goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='leads')
    onboarding_complete = models.BooleanField(default=False)

    # Notifications
    notification_email = models.EmailField(blank=True, null=True)

    # FOMO / engagement
    # cta_mode picks ONE follow-up strategy so we never send both:
    #   'ai'     = AI-generated CTA from visitor behavior (LLM personalises
    #              based on browsing context, EMA signals, heat level). Fires
    #              on behavior triggers (pricing_hesitation, exit_intent, …)
    #              AND as the AFK-nudge text after 2 min idle.
    #   'manual' = use cta_message verbatim as the AFK-nudge text. Behavior
    #              triggers do NOT fire standalone messages.
    #   'off'    = no automated CTAs at all (AI replies still happen).
    CTA_MODE_CHOICES = [
        ('ai',     'AI-generated from behavior'),
        ('manual', 'Manual message'),
        ('off',    'Off — no automated CTAs'),
    ]
    cta_mode = models.CharField(max_length=10, choices=CTA_MODE_CHOICES, default='ai')

    discount_code = models.CharField(max_length=100, blank=True, null=True)
    cta_message = models.CharField(max_length=255, default="You're clearly ready — grab your exclusive discount:")
    fomo_offer_text = models.CharField(max_length=255, blank=True, null=True)
    fomo_countdown_seconds = models.IntegerField(default=600)

    # ── Pre-purchase FAQ blurbs ──────────────────────────────────────────────
    # Short tenant-configurable answers the bot uses when a visitor asks
    # about return policy or shipping BEFORE buying. Without these the bot
    # was deflecting ("share your order number") which kills pre-sale trust.
    # Leave blank to fall back to generic defaults baked into the prompt.
    return_policy_blurb = models.CharField(
        max_length=300, blank=True, default='',
        help_text='Short pre-purchase return policy answer (e.g. "30-day no-questions returns. Free return shipping.")',
    )
    shipping_blurb = models.CharField(
        max_length=300, blank=True, default='',
        help_text='Short pre-purchase shipping answer (e.g. "We ship nationwide in 3-5 business days. Exact rates depend on your area.")',
    )
    # Q8 — Scarcity / urgency line. Bot only deploys this when visitor is
    # at READY_TO_BUY state AND hesitating on price/timing (not on every
    # message). Tenant MUST keep it honest — RULE L (no fabricated stock)
    # still applies; the bot will never invent a number that isn't here.
    scarcity_blurb = models.CharField(
        max_length=300, blank=True, default='',
        help_text='Optional urgency line for late-stage hesitation, e.g. "Our top sellers can go fast — want me to check availability?" or "This sale ends Friday at midnight." Leave blank to disable scarcity prompts.',
    )

    # Ingestion tracking
    ingestion_status = models.CharField(max_length=20, choices=INGESTION_CHOICES, default='PENDING')
    total_pages_ingested = models.IntegerField(default=0)
    last_scraped_at = models.DateTimeField(null=True, blank=True)

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

    # ── Instagram Direct (via Meta Graph API) ─────────────────────────────────
    instagram_business_account_id = models.CharField(max_length=100, blank=True, null=True)
    instagram_access_token = models.CharField(max_length=500, blank=True, null=True)
    instagram_verify_token = models.CharField(max_length=100, blank=True, null=True)
    instagram_enabled = models.BooleanField(default=False)

    # ── Shopify Admin API (order tracking — OAuth offline token) ──────────────
    shopify_shop_domain = models.CharField(max_length=255, blank=True, default='')
    shopify_access_token = models.CharField(max_length=255, blank=True, default='')
    shopify_scopes = models.CharField(max_length=255, blank=True, default='')
    shopify_connected_at = models.DateTimeField(null=True, blank=True)

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

    # ── Active offers / sales (tenant-declared promotions) ────────────────────
    # List of {id, type, title, description, link, starts_at, ends_at, enabled}.
    # The bot mentions live ones in conversation (chat/offers.py); date-gated so
    # they auto-expire. Distinct from the reactive FOMO fields above.
    active_offers = models.JSONField(default=list, blank=True)

    # ── Page-aware proactive triggers (URL → greeting) ────────────────────────
    # Ordered list of page rules; see chat/page_rules.py for the shape + defaults.
    # Empty = use DEFAULT_PAGE_RULES.
    page_rules = models.JSONField(default=list, blank=True)
    assistant_intro = models.CharField(
        max_length=200, default="Hi! I'm your AI Shopping Assistant."
    )
    proactive_notifications_enabled = models.BooleanField(default=True)
    notification_timeout_seconds = models.IntegerField(default=20)
    # Auto-close the open chat window after N seconds idle. 0 = never.
    auto_close_seconds = models.IntegerField(default=0)
    # Delay (seconds) before the page-greeting popup appears after a visitor
    # lands on a page. 0 = show immediately.
    notification_delay_seconds = models.IntegerField(default=0)
    # Manual, STATIC (no-LLM) nudge messages. Blank = disabled.
    #   idle_message → shown as a suggestion bubble when the visitor goes quiet
    #                  (chat closed) for ~45s. Fires once per session.
    #   exit_message → shown on exit-intent ("don't leave yet…"). When set it
    #                  REPLACES the AI-generated exit_intent CTA, so no tokens
    #                  are spent. Blank → fall back to the cta_mode strategy.
    idle_message = models.CharField(max_length=200, blank=True, default='')
    exit_message = models.CharField(max_length=200, blank=True, default='')

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
    # When a super-admin assigns a plan by hand (comp/trial/override), set this
    # so automated Stripe webhook handlers won't silently revert the plan to
    # Free off a stale/retried `customer.subscription.*` event. A genuine new
    # Stripe checkout clears it again.
    manual_plan_override = models.BooleanField(default=False)
    trial_ends_at = models.DateTimeField(blank=True, null=True)
    billing_interval = models.CharField(
        max_length=10, default='monthly',
        choices=[('monthly', 'Monthly'), ('annual', 'Annual')],
    )
    billing_cycle_anchor = models.DateField(blank=True, null=True)

    # ── Per-resource usage counters (reset each billing cycle) ────────────────
    messages_this_month = models.IntegerField(default=0)
    images_this_month = models.IntegerField(default=0)
    voice_this_month = models.IntegerField(default=0)
    videos_this_month = models.IntegerField(default=0)

    # ── Add-on top-ups (purchased, consumed first before plan quota) ──────────
    addon_messages = models.IntegerField(default=0)
    addon_images = models.IntegerField(default=0)
    addon_voice = models.IntegerField(default=0)
    addon_videos = models.IntegerField(default=0)

    # ── V2 scaffolding (DB columns only — no business logic yet) ──────────────
    affiliate_code = models.CharField(max_length=50, blank=True, null=True)
    marketing_messages_enabled = models.BooleanField(default=False)

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


class Invoice(models.Model):
    """Monthly tenant invoice — composed from local data, NOT Stripe.

    We render an invoice for every active tenant at month-end with:
      • subscription line (plan name + period + price)
      • each AddOnPurchase from the period (one line per purchase)
      • usage summary (sessions, leads, addons consumed) — informational,
        not billed (those are already covered by the plan / addon lines)
      • tax line (configurable per tenant; 0% default)
      • total

    Invoice number format: CF-{tenant_id:04d}-{year}{month:02d}-{seq:02d}
    where seq is the ordinal of invoices that month for this tenant
    (almost always 01 — sequence handles edge cases like manual re-issue).
    """
    STATUS_CHOICES = [
        ('draft',  'Draft'),
        ('issued', 'Issued'),
        ('sent',   'Sent (emailed)'),
        ('paid',   'Paid'),
        ('void',   'Void'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('TenantProfile', on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=32, unique=True)

    # Billing period (inclusive)
    period_start = models.DateField()
    period_end = models.DateField()

    # Snapshots at issue time so historical invoices don't change if plan price
    # is later edited.
    plan_name_at_issue = models.CharField(max_length=100, blank=True)
    company_name_at_issue = models.CharField(max_length=255, blank=True)
    recipient_email_at_issue = models.EmailField(blank=True)

    # Branding snapshot — frozen at issue time. Sourced from the tenant's
    # first Client (chatbot_logo_url / chatbot_color). Frozen here so
    # historical invoices keep showing the brand the customer was using
    # back then, even if they redesign next year.
    brand_logo_url_at_issue = models.URLField(max_length=500, blank=True, default='')
    brand_color_at_issue = models.CharField(max_length=20, blank=True, default='')

    # Money (all USD; we render with locale where appropriate)
    subtotal_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0..100
    tax_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Line items + usage summary as JSON snapshots — frozen at issue time
    line_items = models.JSONField(default=list)
    # Each: { 'description': str, 'quantity': int, 'unit_price_usd': str, 'amount_usd': str }
    usage_summary = models.JSONField(default=dict)
    # { 'sessions': int, 'leads': int, 'hot_leads': int, 'ai_messages': int,
    #   'images': int, 'voice': int, 'videos': int, 'top_pages': [...] }

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-period_start', '-created_at']
        indexes = [
            models.Index(fields=['tenant', '-period_start']),
            models.Index(fields=['status', '-created_at']),
        ]
        unique_together = [('tenant', 'period_start')]  # one invoice per tenant per period

    def __str__(self):
        return f'{self.invoice_number} — {self.tenant} (${self.total_usd})'

    @property
    def is_zero_billed(self):
        return self.total_usd == 0


class AddOnPurchase(models.Model):
    """One-time top-up credits bought outside the subscription quota.

    When a tenant exhausts their plan's monthly message/image/voice/video
    quota they can buy more here, one purchase at a time. Each row is the
    audit record for a Stripe one-time PaymentIntent; on
    payment_intent.succeeded we add the credits to the corresponding
    TenantProfile.addon_* field.

    These credits never expire automatically — they sit on the tenant
    until consumed. (Refund handled by zeroing the addon_* counter and
    issuing the Stripe refund via the customer portal.)
    """
    KIND_CHOICES = [
        ('message', 'Messages'),
        ('image',   'Images'),
        ('voice',   'Voice commands'),
        ('video',   'Videos'),
    ]
    STATUS_CHOICES = [
        ('pending',   'Pending'),     # Stripe Checkout created, awaiting payment
        ('succeeded', 'Succeeded'),   # Stripe payment_intent.succeeded — credits applied
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='addon_purchases')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    quantity = models.IntegerField()              # number of credits purchased
    unit_price_usd = models.DecimalField(max_digits=8, decimal_places=4)  # snapshot
    total_paid_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')

    stripe_checkout_session_id = models.CharField(max_length=200, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True, unique=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f'{self.tenant} — {self.quantity} {self.kind} ({self.status})'


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


class PlatformConfig(models.Model):
    """Singleton — exactly one row (pk=1). Stores platform-level AI config."""
    openrouter_api_key = models.CharField(max_length=255, blank=True, default='')
    primary_model      = models.CharField(max_length=200, default='google/gemini-2.0-flash-001')
    updated_at         = models.DateTimeField(auto_now=True)
    updated_by         = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )

    class Meta:
        verbose_name = 'Platform Config'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        from django.core.cache import cache
        cache.delete('platform_config')


# ═══════════════════════════════════════════════════════════════════════════════
# F14 — V2 ARCHITECTURE STUBS
#
# IMPORTANT: These models exist to LOCK IN the schema shape so V2 features
# can be lit up without painful migrations on hot tables. They are NOT
# wired to any views, admin pages, Celery tasks, or webhooks today.
#
# Do NOT add fields to TenantProfile/Client/ChatSession for V2 features
# without adding them HERE first — that's the whole point. When V2 ships:
#   - Affiliate: add views/admin to read AffiliateProfile + AffiliateConversion
#   - Marketing: add views to create MarketingCampaign, fan-out delivery
#                rows on send, track delivery status from webhook callbacks
# ═══════════════════════════════════════════════════════════════════════════════

class AffiliateProfile(models.Model):
    """V2: Affiliate program — tenants who refer other tenants earn commission.

    Stub only — no UI/API today. When V2 ships, a signup flow assigns each
    affiliate a unique referral_code, that code lands in new-tenant signup
    URLs as ?ref=<code>, and we record the AffiliateConversion below at
    plan checkout time.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='affiliate_profile')
    referral_code = models.CharField(max_length=32, unique=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.20)  # 20% default
    payout_email = models.EmailField(blank=True)  # PayPal / wire info
    is_active = models.BooleanField(default=True)
    total_earned_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # lifetime
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['referral_code'])]

    def __str__(self):
        return f'Affiliate<{self.user.username}, code={self.referral_code}>'


class AffiliateConversion(models.Model):
    """V2: a referred tenant subscribed to a paid plan.

    One row per qualifying event. We compute commission at write time from
    affiliate.commission_rate × plan price so historical changes don't
    re-bill past conversions. payout_status tracks the lifecycle:
    pending → ready (awaiting batch) → paid → reversed (refund/chargeback).
    """
    STATUS_CHOICES = [
        ('pending',  'Pending qualification period'),  # e.g. 30-day refund window
        ('ready',    'Ready to pay out'),
        ('paid',     'Paid'),
        ('reversed', 'Reversed (refund/chargeback)'),
    ]

    id = models.BigAutoField(primary_key=True)
    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.PROTECT, related_name='conversions')
    referred_tenant = models.ForeignKey('TenantProfile', on_delete=models.SET_NULL, null=True, related_name='+')
    plan = models.ForeignKey('Plan', on_delete=models.SET_NULL, null=True, related_name='+')
    plan_price_at_event_usd = models.DecimalField(max_digits=8, decimal_places=2)
    commission_usd = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    stripe_subscription_id = models.CharField(max_length=200, blank=True)  # source of truth
    created_at = models.DateTimeField(auto_now_add=True)
    qualified_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['affiliate', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f'Conversion<{self.affiliate} → tenant {self.referred_tenant_id}, ${self.commission_usd}>'


class MarketingCampaign(models.Model):
    """V2: Pro-plan-only outbound marketing campaigns.

    Stub only — no send pipeline today. When V2 ships, scheduled_at + status
    drive a Celery task that fans out one MarketingDelivery per recipient
    Visitor (whose marketing_opt_out is False).
    """
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending',   'Sending'),
        ('sent',      'Sent'),
        ('canceled',  'Canceled'),
    ]
    CHANNEL_CHOICES = [
        ('email',    'Email'),
        ('whatsapp', 'WhatsApp'),
        ('sms',      'SMS'),
    ]

    id = models.BigAutoField(primary_key=True)
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='marketing_campaigns')
    name = models.CharField(max_length=200)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='email')
    subject = models.CharField(max_length=255, blank=True)         # email only
    body = models.TextField(blank=True)
    target_filter_json = models.JSONField(default=dict, blank=True)  # e.g. {'kanban_state': 'HOT_LEAD'}
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['status', 'scheduled_at']),
        ]

    def __str__(self):
        return f'Campaign<{self.client.name}/{self.name} {self.status}>'


class MarketingDelivery(models.Model):
    """V2: one row per (campaign × recipient). Tracks delivery + click telemetry."""
    STATUS_CHOICES = [
        ('queued',    'Queued'),
        ('sent',      'Sent'),
        ('delivered', 'Delivered (provider confirmed)'),
        ('opened',    'Opened (email pixel / link click)'),
        ('clicked',   'CTA clicked'),
        ('bounced',   'Bounced'),
        ('unsubscribed', 'Unsubscribed'),
        ('failed',    'Failed'),
    ]

    id = models.BigAutoField(primary_key=True)
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='deliveries')
    # Recipient can be either an anonymous Visitor or a known TenantProfile member
    visitor = models.ForeignKey('chat.Visitor', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=14, choices=STATUS_CHOICES, default='queued')
    provider_message_id = models.CharField(max_length=200, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['recipient_email']),
        ]

    def __str__(self):
        return f'Delivery<{self.campaign_id} → {self.recipient_email or self.recipient_phone}>'

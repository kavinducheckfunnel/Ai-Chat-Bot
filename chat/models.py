import uuid
from django.db import models
from django.contrib.auth.models import User
from users.models import Client


class Visitor(models.Model):
    """
    One real-world person across multiple sessions.

    The widget generates a UUID and stores it in localStorage (cf_visitor_<client_id>)
    so the same browser maps to the same Visitor across days/sessions. Each Visitor
    aggregates lifetime stats (sessions, messages, page views, clicks) and the most
    recent EMA scores so the AI / dashboard can reason about returning visitors.
    """
    visitor_uid = models.CharField(max_length=64, db_index=True)
    client      = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='visitors', db_index=True)
    first_seen  = models.DateTimeField(auto_now_add=True)
    last_seen   = models.DateTimeField(auto_now=True)

    # Aggregate stats across all sessions
    total_sessions      = models.IntegerField(default=0)
    total_messages      = models.IntegerField(default=0)
    total_page_views    = models.IntegerField(default=0)
    total_time_seconds  = models.IntegerField(default=0)
    total_clicks        = models.IntegerField(default=0)
    total_atc_clicks    = models.IntegerField(default=0)

    # Latest known EMA scores (carried over from the most recent session)
    intent_ema   = models.FloatField(default=0)
    budget_ema   = models.FloatField(default=0)
    urgency_ema  = models.FloatField(default=0)

    # Contact info (filled when a lead is captured in any session)
    lead_email   = models.EmailField(blank=True)
    lead_phone   = models.CharField(max_length=50, blank=True)
    lead_name    = models.CharField(max_length=200, blank=True)

    # Visitor metadata (best-known values)
    device        = models.CharField(max_length=20, blank=True)
    os            = models.CharField(max_length=20, blank=True)
    browser       = models.CharField(max_length=20, blank=True)
    country       = models.CharField(max_length=100, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    country_code  = models.CharField(max_length=10, blank=True)
    timezone      = models.CharField(max_length=64, blank=True)
    ip            = models.CharField(max_length=64, blank=True)

    # Top interest (most-dwelled product across all sessions, recomputed periodically)
    top_interest_title = models.CharField(max_length=300, blank=True)
    top_interest_url   = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['visitor_uid', 'client'], name='uniq_visitor_per_client'),
        ]
        indexes = [
            models.Index(fields=['client', '-last_seen']),
        ]

    def __str__(self):
        label = self.lead_email or self.visitor_uid[:12]
        return f"Visitor {label} ({self.client.name})"


class ChatSession(models.Model):
    TREND_CHOICES = [
        ('UP', 'Up'),
        ('DOWN', 'Down'),
        ('FLAT', 'Flat')
    ]

    STATE_CHOICES = [
        ('RESEARCH', 'Research Mode'),
        ('EVALUATION', 'Evaluation Mode'),
        ('OBJECTION', 'Objection Mode'),
        ('RECOVERY', 'Recovery Mode'),
        ('READY_TO_BUY', 'Ready to Buy')
    ]

    KANBAN_CHOICES = [
        ('NEW', 'New'),
        ('ENGAGED', 'Engaged'),
        ('HOT_LEAD', 'Hot Lead'),
        ('CONVERTED', 'Converted'),
        ('LOST', 'Lost'),
    ]

    CHANNEL_CHOICES = [
        ('website', 'Website'),
        ('whatsapp', 'WhatsApp'),
        ('messenger', 'Messenger'),
        ('telegram', 'Telegram'),
    ]

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    visitor_id = models.CharField(max_length=255, db_index=True)
    # FK link to the persistent cross-session Visitor record (set on connect
    # via the localStorage cf_visitor_<client_id> UUID from the widget).
    # Named `visitor_obj` to avoid clashing with the legacy `visitor_id`
    # CharField above — Django would otherwise auto-derive `visitor_id` for
    # the FK accessor and collide.
    visitor_obj = models.ForeignKey(
        'Visitor', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sessions', db_index=True,
        db_column='visitor_obj_id',
    )

    current_intent_ema = models.FloatField(default=0.0)
    current_budget_ema = models.FloatField(default=0.0)
    current_urgency_ema = models.FloatField(default=0.0)

    previous_intent_ema = models.FloatField(default=0.0)
    previous_budget_ema = models.FloatField(default=0.0)
    previous_urgency_ema = models.FloatField(default=0.0)

    intent_trend = models.CharField(max_length=10, choices=TREND_CHOICES, default='FLAT')
    budget_trend = models.CharField(max_length=10, choices=TREND_CHOICES, default='FLAT')
    urgency_trend = models.CharField(max_length=10, choices=TREND_CHOICES, default='FLAT')

    conversation_state = models.CharField(max_length=20, choices=STATE_CHOICES, default='RESEARCH')
    kanban_state = models.CharField(max_length=20, choices=KANBAN_CHOICES, default='NEW')

    # Persisted heat score (updated on every AI response)
    heat_score = models.FloatField(default=0.0)

    message_count = models.IntegerField(default=0)
    chat_history = models.JSONField(default=list)
    chat_history_archive = models.JSONField(default=list)
    behavioral_context = models.JSONField(default=dict)

    lead_email = models.EmailField(null=True, blank=True)
    lead_phone = models.CharField(max_length=50, null=True, blank=True)

    # Visitor fingerprint — populated on first WebSocket connect
    visitor_ip = models.GenericIPAddressField(null=True, blank=True)
    visitor_country = models.CharField(max_length=100, null=True, blank=True)
    visitor_city = models.CharField(max_length=100, null=True, blank=True)
    visitor_country_code = models.CharField(max_length=10, null=True, blank=True)
    visitor_device = models.CharField(max_length=20, null=True, blank=True)   # desktop / mobile / tablet
    visitor_os = models.CharField(max_length=50, null=True, blank=True)       # Windows / macOS / iOS / Android / Linux
    visitor_browser = models.CharField(max_length=50, null=True, blank=True)  # Chrome / Safari / Firefox / Edge
    visitor_referrer = models.URLField(max_length=2000, null=True, blank=True)
    visitor_timezone = models.CharField(max_length=100, null=True, blank=True)
    page_visits = models.JSONField(default=list)  # [{url, title, duration_seconds, visited_at}]

    # Channel source
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='website')

    # God View — admin takeover
    takeover_active = models.BooleanField(default=False)
    taken_over_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='takeover_sessions'
    )

    # Trigger flags
    closing_triggered = models.BooleanField(default=False)
    afk_nudge_sent = models.BooleanField(default=False)
    nudge_count = models.IntegerField(default=0)
    last_nudge_at = models.DateTimeField(null=True, blank=True)
    last_visitor_message_at = models.DateTimeField(null=True, blank=True)

    # Conversation tags — tenant-applied labels e.g. ["Support", "VIP"]
    tags = models.JSONField(default=list, blank=True)

    # Email notification flags
    hot_lead_email_sent = models.BooleanField(default=False)
    human_requested = models.BooleanField(default=False)

    # Set true the first time we push a 'lead_capture_required' event to the
    # widget so the modal doesn't re-pop on every subsequent AI reply.
    # See chat.consumers.AsyncChatConsumer._maybe_prompt_lead_capture.
    lead_capture_prompted = models.BooleanField(default=False)

    # ── E1 — Outcome tagging for conversion KPI tracking ─────────────────
    # Single canonical session outcome. Used to compute CVR/CER/OHR/ESC/ABN
    # metrics on the KPI dashboard. Auto-set when the session ends or on a
    # nightly sweep (chat.tasks.tag_session_outcomes). Manual override
    # possible from the Inbox UI for cases the heuristic mislabelled.
    OUTCOME_CHOICES = [
        ('open',       'Still in conversation'),   # default until classified
        ('converted',  'Converted'),               # kanban_state == CONVERTED
        ('captured',   'Contact captured'),        # has lead_email or lead_phone, not converted
        ('escalated',  'Escalated to human'),      # taken_over_by is set
        ('abandoned',  'Abandoned mid-chat'),      # idle 30+ min, no contact, no conversion
        ('ghost',      'Ghost session (no messages)'),  # message_count == 0 → exclude from KPIs
    ]
    outcome = models.CharField(max_length=12, choices=OUTCOME_CHOICES, default='open', db_index=True)
    outcome_set_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.session_id)


class LLMCallLog(models.Model):
    """
    One row per LLM API call. Foundation for MLOps observability:
      - cost dashboard (sum cost_usd by client / day / model)
      - fallback monitoring (count where fallback_from != '')
      - quality regressions (group by prompt_hash, compare reactions)
      - rate-limit hotspots (filter status='rate_limited')
      - BYOK vs platform spend split (group by is_byok)

    Written by chat.ai_service._invoke_with_fallback after every llm.invoke().
    Best-effort: logging failure must never bubble up and break a chat reply,
    so writes are wrapped in try/except in the call site.
    """
    STATUS_CHOICES = [
        ('ok',            'OK'),
        ('rate_limited',  'Rate Limited'),
        ('error',         'Error'),
        ('fallback_used', 'Fallback Used'),  # ok ultimately, but not on primary model
    ]

    id = models.BigAutoField(primary_key=True)
    # Nullable so platform-only calls (no client context) still log.
    client  = models.ForeignKey('users.Client', null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='llm_calls')
    session = models.ForeignKey('chat.ChatSession', null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='llm_calls')

    # Identity of the call
    model    = models.CharField(max_length=120)   # e.g. 'openai/gpt-4o-mini'
    provider = models.CharField(max_length=20)    # 'openrouter' | 'openai' | 'anthropic'
    is_byok  = models.BooleanField(default=False)

    # Performance
    latency_ms        = models.IntegerField()
    prompt_tokens     = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    total_tokens      = models.IntegerField(null=True, blank=True)

    # Estimated cost in USD. For BYOK calls the cost lands on the tenant;
    # for platform calls it's our P&L. Cost is computed at write-time from
    # a static price table per model + token usage.
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    # Outcome
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ok')
    fallback_from = models.CharField(max_length=120, blank=True)
    error_message = models.TextField(blank=True)

    # Stable hash of the system prompt — used for prompt A/B testing later.
    prompt_hash = models.CharField(max_length=16, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client',   '-created_at']),
            models.Index(fields=['status',   '-created_at']),
            models.Index(fields=['model',    '-created_at']),
            models.Index(fields=['is_byok',  '-created_at']),
        ]

    def __str__(self):
        return f'{self.model} {self.status} {self.latency_ms}ms'


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT EDITOR
#
# Lets the super admin edit the live system prompt from the UI. One row per
# editable slot in `PromptTemplate`; every save creates a new immutable
# `PromptVersion`. The `active_version` pointer is what `chat.prompt_service`
# resolves at runtime. The file constants in `chat.prompts` remain the
# factory default — if no DB version is active (fresh install, DB error),
# the file content is used.
# ─────────────────────────────────────────────────────────────────────────────

class PromptTemplate(models.Model):
    """Catalog of editable prompt slots. Seeded once with the two slots we expose."""

    SLUG_CHOICES = (
        ('system_persona', 'System Persona'),
    )

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug        = models.SlugField(max_length=64, unique=True, choices=SLUG_CHOICES)
    description = models.TextField(blank=True)

    # Pointer to the version currently in use. NULL only briefly during
    # initial seed; the runtime resolver falls back to the file constant
    # in that case.
    active_version = models.ForeignKey(
        'PromptVersion',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='active_for',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['slug']

    def __str__(self):
        return f'PromptTemplate<{self.slug}>'


class PromptVersion(models.Model):
    """Immutable history. New row per save. Rollback = new row pointing back."""

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template    = models.ForeignKey(
        PromptTemplate, on_delete=models.CASCADE, related_name='versions'
    )
    version     = models.PositiveIntegerField()  # monotonic per template (1, 2, 3, …)
    body        = models.TextField()
    notes       = models.CharField(max_length=500, blank=True)
    created_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='prompt_versions',
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    # True for the seed version that captures the file constants on first migration.
    is_default  = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('template', 'version')]
        indexes = [
            models.Index(fields=['template', '-created_at']),
        ]

    def __str__(self):
        return f'PromptVersion<{self.template.slug} v{self.version}>'

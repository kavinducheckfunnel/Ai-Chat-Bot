import uuid
from django.db import models
from django.contrib.auth.models import User
from users.models import Client


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

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    visitor_id = models.CharField(max_length=255, db_index=True)

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

    # Email notification flags
    hot_lead_email_sent = models.BooleanField(default=False)
    human_requested = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.session_id)

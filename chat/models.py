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

    # Heat score — computed from EMA scores on every message
    heat_score = models.FloatField(default=0.0)

    message_count = models.IntegerField(default=0)
    chat_history = models.JSONField(default=list)
    behavioral_context = models.JSONField(default=dict)

    # God View / Human Takeover
    taken_over_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='takeover_sessions'
    )
    takeover_active = models.BooleanField(default=False)

    # Engagement triggers
    closing_triggered = models.BooleanField(default=False)
    afk_nudge_sent = models.BooleanField(default=False)
    nudge_count = models.IntegerField(default=0)
    last_nudge_at = models.DateTimeField(null=True, blank=True)
    last_visitor_message_at = models.DateTimeField(null=True, blank=True)

    # Lead capture
    lead_email = models.EmailField(null=True, blank=True)
    lead_phone = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.session_id)

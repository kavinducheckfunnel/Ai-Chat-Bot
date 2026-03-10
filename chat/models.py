import uuid
from django.db import models

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

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
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
    
    message_count = models.IntegerField(default=0)
    chat_history = models.JSONField(default=list)
    behavioral_context = models.JSONField(default=dict)

    lead_email = models.EmailField(null=True, blank=True)
    lead_phone = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.session_id)

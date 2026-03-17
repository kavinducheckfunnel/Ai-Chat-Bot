from django.db import models
from users.models import Client


class AnalyticEvent(models.Model):
    EVENT_CHOICES = [
        ('page_view', 'Page View'),
        ('pricing_visit', 'Pricing Page Visit'),
        ('exit_intent', 'Exit Intent'),
        ('scroll_depth', 'Scroll Depth'),
        ('session_start', 'Session Start'),
        ('beacon', 'Beacon'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='analytic_events', null=True, blank=True)
    session_id = models.CharField(max_length=255, db_index=True)
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES, default='beacon')
    page_url = models.CharField(max_length=2000, blank=True, null=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id', 'event_type']),
            models.Index(fields=['client', 'created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} | session={self.session_id}"

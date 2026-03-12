import uuid
from django.db import models

class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    domain_url = models.URLField(max_length=500, blank=True, null=True)
    platform = models.CharField(max_length=50, choices=[('WORDPRESS', 'WordPress'), ('SHOPIFY', 'Shopify'), ('CUSTOM', 'Custom')], default='WORDPRESS')
    
    # Store API limits, subscription status, or secret tokens for webhooks here later
    webhook_secret = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.domain_url})"

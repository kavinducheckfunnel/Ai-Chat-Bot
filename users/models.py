import uuid
from django.db import models

class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    domain_url = models.URLField(max_length=500, blank=True, null=True)
    platform = models.CharField(max_length=50, choices=[('WORDPRESS', 'WordPress'), ('SHOPIFY', 'Shopify'), ('CUSTOM', 'Custom')], default='WORDPRESS')
    
    # Branding & Configuration
    is_active = models.BooleanField(default=True)
    plan = models.CharField(max_length=50, choices=[('FREE', 'Free'), ('PRO', 'Pro'), ('ENTERPRISE', 'Enterprise')], default='FREE')
    chatbot_name = models.CharField(max_length=100, default='AI Assistant')
    chatbot_color = models.CharField(max_length=7, default='#3B82F6')  # Default blue
    chatbot_logo_url = models.URLField(max_length=1000, blank=True, null=True)
    
    # Ingestion Status
    ingestion_status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('RUNNING', 'Running'), ('DONE', 'Done'), ('FAILED', 'Failed')], default='PENDING')
    total_pages_ingested = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.domain_url})"

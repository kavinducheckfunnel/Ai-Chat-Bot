import uuid
from django.db import models
from django.contrib.auth.models import User


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    max_clients = models.IntegerField(default=1)
    max_sessions_per_month = models.IntegerField(default=500)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class Client(models.Model):
    PLATFORM_CHOICES = [
        ('WORDPRESS', 'WordPress'),
        ('SHOPIFY', 'Shopify'),
        ('CUSTOM', 'Custom'),
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

    # FOMO / engagement
    discount_code = models.CharField(max_length=100, blank=True, null=True)
    cta_message = models.CharField(max_length=255, default="You're clearly ready — grab your exclusive discount:")
    fomo_offer_text = models.CharField(max_length=255, blank=True, null=True)
    fomo_countdown_seconds = models.IntegerField(default=600)

    # Ingestion tracking
    ingestion_status = models.CharField(max_length=20, choices=INGESTION_CHOICES, default='PENDING')
    total_pages_ingested = models.IntegerField(default=0)

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

    def __str__(self):
        return f"{self.company_name or self.user.username}"

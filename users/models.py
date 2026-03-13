import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ─────────────────────────────────────────────────────────────────────────────
# Plan — billing tier for a tenant
# ─────────────────────────────────────────────────────────────────────────────

class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    max_clients = models.IntegerField(default=1)
    max_sessions_per_month = models.IntegerField(default=500)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# Client — represents one chatbot / website for a tenant
# ─────────────────────────────────────────────────────────────────────────────

class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    domain_url = models.URLField(max_length=500, blank=True, null=True)
    platform = models.CharField(
        max_length=50,
        choices=[('WORDPRESS', 'WordPress'), ('SHOPIFY', 'Shopify'), ('CUSTOM', 'Custom')],
        default='WORDPRESS',
    )

    # Branding & Configuration
    is_active = models.BooleanField(default=True)
    chatbot_name = models.CharField(max_length=100, default='AI Assistant')
    chatbot_color = models.CharField(max_length=7, default='#3B82F6')
    chatbot_logo_url = models.URLField(max_length=1000, blank=True, null=True)

    # Engagement triggers
    discount_code = models.CharField(max_length=100, blank=True, null=True)
    cta_message = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        default="You're clearly ready — grab your exclusive discount:",
    )
    fomo_offer_text = models.CharField(max_length=500, blank=True, null=True)
    fomo_countdown_seconds = models.IntegerField(default=600)

    # Ingestion Status
    ingestion_status = models.CharField(
        max_length=20,
        choices=[('PENDING', 'Pending'), ('RUNNING', 'Running'), ('DONE', 'Done'), ('FAILED', 'Failed')],
        default='PENDING',
    )
    total_pages_ingested = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.domain_url})"


# ─────────────────────────────────────────────────────────────────────────────
# UserProfile — extends Django's built-in User with role + tenant link
# ─────────────────────────────────────────────────────────────────────────────

ROLE_CHOICES = [
    ('superadmin', 'Super Admin'),
    ('tenant_admin', 'Tenant Admin'),
    ('end_user', 'End User'),
]


class UserProfile(models.Model):
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


# ─────────────────────────────────────────────────────────────────────────────
# TenantProfile — links a tenant_admin user to their Client(s)
# ─────────────────────────────────────────────────────────────────────────────

class TenantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tenant_profile')
    clients = models.ManyToManyField(Client, blank=True, related_name='tenant_owners')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    sessions_this_month = models.IntegerField(default=0)
    company_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Tenant: {self.user.username}"


# ─────────────────────────────────────────────────────────────────────────────
# Auto-create UserProfile on User creation
# ─────────────────────────────────────────────────────────────────────────────

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

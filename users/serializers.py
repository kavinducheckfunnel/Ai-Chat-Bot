from rest_framework import serializers
from .models import Client, UserProfile, TenantProfile, Plan
from django.contrib.auth.models import User


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'max_clients', 'max_sessions_per_month', 'price_monthly']


class ClientSerializer(serializers.ModelSerializer):
    session_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'domain_url', 'platform',
            'is_active', 'chatbot_name', 'chatbot_color', 'chatbot_logo_url',
            'notification_email',
            'discount_code', 'cta_message', 'fomo_offer_text', 'fomo_countdown_seconds',
            'ingestion_status', 'total_pages_ingested', 'session_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'session_count', 'ingestion_status', 'total_pages_ingested']


class ClientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['name', 'domain_url', 'platform']


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    is_superuser = serializers.BooleanField(source='user.is_superuser', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'role', 'is_superuser', 'is_superadmin', 'is_tenant_admin']

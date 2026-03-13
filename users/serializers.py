from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile, TenantProfile, Client, Plan


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'domain_url', 'platform', 'is_active',
            'chatbot_name', 'chatbot_color', 'chatbot_logo_url',
            'discount_code', 'cta_message', 'fomo_offer_text', 'fomo_countdown_seconds',
            'ingestion_status', 'total_pages_ingested', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'ingestion_status', 'total_pages_ingested']


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'max_clients', 'max_sessions_per_month', 'price_monthly']


class TenantProfileSerializer(serializers.ModelSerializer):
    clients = ClientSerializer(many=True, read_only=True)
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = TenantProfile
        fields = ['company_name', 'clients', 'plan', 'sessions_this_month']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    tenant_profile = TenantProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile', 'tenant_profile']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=['superadmin', 'tenant_admin', 'end_user'],
        default='tenant_admin',
        write_only=True,
    )
    company_name = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'company_name']

    def create(self, validated_data):
        role = validated_data.pop('role', 'tenant_admin')
        company_name = validated_data.pop('company_name', '')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        # UserProfile is auto-created by signal; set the role
        user.profile.role = role
        user.profile.save()
        # Create TenantProfile if tenant_admin
        if role == 'tenant_admin':
            TenantProfile.objects.get_or_create(user=user, defaults={'company_name': company_name})
        return user


class TenantAdminSerializer(serializers.ModelSerializer):
    """Used by superadmin to list/manage tenants."""
    profile = UserProfileSerializer(read_only=True)
    tenant_profile = TenantProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'profile', 'tenant_profile']
        read_only_fields = ['id', 'date_joined']

from django.contrib import admin
from .models import Client, Plan, UserProfile, TenantProfile


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain_url', 'platform', 'is_active', 'ingestion_status', 'created_at']
    list_filter = ['platform', 'is_active', 'ingestion_status']
    search_fields = ['name', 'domain_url']


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_clients', 'max_sessions_per_month', 'price_monthly']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']


@admin.register(TenantProfile)
class TenantProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'plan', 'sessions_this_month']
    filter_horizontal = ['clients']

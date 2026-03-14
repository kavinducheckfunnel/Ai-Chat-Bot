from django.contrib import admin
from .models import Plan, Client, UserProfile, TenantProfile


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_clients', 'max_sessions_per_month', 'price_monthly')
    search_fields = ('name',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain_url', 'platform', 'is_active', 'ingestion_status', 'total_pages_ingested', 'created_at')
    list_filter = ('platform', 'is_active', 'ingestion_status')
    search_fields = ('name', 'domain_url')
    readonly_fields = ('created_at', 'updated_at', 'webhook_secret')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


@admin.register(TenantProfile)
class TenantProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'plan', 'sessions_this_month')
    list_filter = ('plan',)
    search_fields = ('company_name', 'user__username')
    filter_horizontal = ('clients',)

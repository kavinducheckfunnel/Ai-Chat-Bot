from django.contrib import admin
from .models import ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        'session_id', 'client', 'visitor_id', 'heat_score',
        'conversation_state', 'kanban_state', 'message_count',
        'takeover_active', 'closing_triggered', 'updated_at',
    )
    list_filter = ('conversation_state', 'kanban_state', 'takeover_active', 'closing_triggered', 'client')
    search_fields = ('visitor_id', 'lead_email', 'lead_phone')
    readonly_fields = ('session_id', 'created_at', 'updated_at', 'heat_score')
    ordering = ('-updated_at',)

    fieldsets = (
        ('Session Info', {
            'fields': ('session_id', 'client', 'visitor_id', 'heat_score')
        }),
        ('EMA Scores', {
            'fields': (
                'current_intent_ema', 'current_budget_ema', 'current_urgency_ema',
                'previous_intent_ema', 'previous_budget_ema', 'previous_urgency_ema',
                'intent_trend', 'budget_trend', 'urgency_trend',
            )
        }),
        ('State', {
            'fields': ('conversation_state', 'kanban_state', 'message_count')
        }),
        ('Lead Info', {
            'fields': ('lead_email', 'lead_phone')
        }),
        ('God View', {
            'fields': ('takeover_active', 'taken_over_by')
        }),
        ('Triggers', {
            'fields': ('closing_triggered', 'afk_nudge_sent', 'last_visitor_message_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

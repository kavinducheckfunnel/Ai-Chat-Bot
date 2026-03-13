from django.contrib import admin
from .models import ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id', 'visitor_id', 'client', 'conversation_state',
        'heat_score', 'message_count', 'takeover_active', 'updated_at',
    ]
    list_filter = ['conversation_state', 'takeover_active', 'client']
    search_fields = ['visitor_id', 'session_id']
    readonly_fields = ['session_id', 'created_at', 'updated_at', 'chat_history']
    ordering = ['-heat_score', '-updated_at']

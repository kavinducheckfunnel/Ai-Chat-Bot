import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import User


class AdminDashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the real-time admin dashboard.
    URL: ws/admin/dashboard/?token=<jwt>

    Groups joined:
      - dashboard_all          (for superadmin)
      - dashboard_<client_id>  (for tenant admin, one per owned client)
    """

    async def connect(self):
        # Authenticate via JWT in query string
        token = self._get_token_from_query()
        user = await self._get_user_from_token(token)
        if user is None:
            await self.close(code=4001)
            return

        self.user = user
        self.groups = []

        role = await self._get_role(user)
        if role == 'superadmin':
            self.groups = ['dashboard_all']
        elif role == 'tenant_admin':
            client_ids = await self._get_tenant_client_ids(user)
            self.groups = [f'dashboard_{cid}' for cid in client_ids]
            self.groups.append('dashboard_all')  # superadmin updates still flow
        else:
            await self.close(code=4003)
            return

        for group in self.groups:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()

        # Send initial snapshot of active sessions
        snapshot = await self._get_active_sessions(user, role)
        await self.send(text_data=json.dumps({'type': 'snapshot', 'sessions': snapshot}))

    async def disconnect(self, code):
        for group in getattr(self, 'groups', []):
            await self.channel_layer.group_discard(group, self.channel_name)

    # ── Receive from admin client (e.g. filter request) ──────────────────
    async def receive(self, text_data):
        pass  # Reserved for future filter/command messages from admin

    # ── Handler: session_update events pushed by ema_engine ──────────────
    async def session_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'session_update',
            **{k: v for k, v in event.items() if k != 'type'},
        }))

    # ── Helpers ───────────────────────────────────────────────────────────
    def _get_token_from_query(self):
        query_string = self.scope.get('query_string', b'').decode()
        for part in query_string.split('&'):
            if part.startswith('token='):
                return part[6:]
        return None

    @database_sync_to_async
    def _get_user_from_token(self, token):
        if not token:
            return None
        try:
            validated = UntypedToken(token)
            user_id = validated['user_id']
            return User.objects.select_related('profile').get(pk=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist):
            return None

    @database_sync_to_async
    def _get_role(self, user):
        try:
            return user.profile.role
        except Exception:
            return None

    @database_sync_to_async
    def _get_tenant_client_ids(self, user):
        try:
            return list(user.tenant_profile.clients.values_list('id', flat=True))
        except Exception:
            return []

    @database_sync_to_async
    def _get_active_sessions(self, user, role):
        from chat.models import ChatSession
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(minutes=30)
        qs = ChatSession.objects.filter(updated_at__gte=cutoff).select_related('client')

        if role == 'tenant_admin':
            try:
                client_ids = list(user.tenant_profile.clients.values_list('id', flat=True))
                qs = qs.filter(client_id__in=client_ids)
            except Exception:
                return []

        qs = qs.order_by('-heat_score')[:50]
        return [
            {
                'session_id': str(s.session_id),
                'heat_score': s.heat_score,
                'conversation_state': s.conversation_state,
                'intent_ema': round(s.current_intent_ema, 3),
                'budget_ema': round(s.current_budget_ema, 3),
                'urgency_ema': round(s.current_urgency_ema, 3),
                'message_count': s.message_count,
                'last_message_at': s.updated_at.isoformat() if s.updated_at else None,
                'visitor_id': s.visitor_id,
                'takeover_active': s.takeover_active,
                'taken_over_by': s.taken_over_by_id,
                'client_id': str(s.client_id) if s.client_id else None,
                'client_name': s.client.name if s.client else None,
            }
            for s in qs
        ]


class GodViewConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for God View — admin watches a specific session live.
    URL: ws/admin/sessions/<session_id>/

    Joins the group: chat_<session_id> so admin sees all messages in real time.
    """

    async def connect(self):
        token = self._get_token_from_query()
        user = await self._get_user_from_token(token)
        if user is None:
            await self.close(code=4001)
            return

        role = await self._get_role(user)
        if role not in ('superadmin', 'tenant_admin'):
            await self.close(code=4003)
            return

        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"chat_{self.session_id}"
        self.admin_group = f"admin_{self.session_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add(self.admin_group, self.channel_name)
        await self.accept()

        # Send full chat history
        history = await self._get_chat_history(self.session_id)
        await self.send(text_data=json.dumps({'type': 'history', 'messages': history}))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.channel_layer.group_discard(self.admin_group, self.channel_name)

    async def receive(self, text_data):
        """Admin sends a message directly into the chat (bypassing AI)."""
        data = json.loads(text_data)
        if data.get('type') == 'admin_message':
            msg = data.get('message', '').strip()
            if not msg:
                return
            await self._append_to_history(self.session_id, 'ai', msg)
            await self.channel_layer.group_send(
                self.group_name,
                {'type': 'chat_message', 'message': msg, 'sender': 'ai', 'admin_injected': True}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event.get('message', ''),
            'sender': event.get('sender', 'ai'),
            'admin_injected': event.get('admin_injected', False),
        }))

    async def session_update(self, event):
        await self.send(text_data=json.dumps({'type': 'session_update', **event}))

    def _get_token_from_query(self):
        query_string = self.scope.get('query_string', b'').decode()
        for part in query_string.split('&'):
            if part.startswith('token='):
                return part[6:]
        return None

    @database_sync_to_async
    def _get_user_from_token(self, token):
        if not token:
            return None
        try:
            validated = UntypedToken(token)
            user_id = validated['user_id']
            return User.objects.select_related('profile').get(pk=user_id)
        except Exception:
            return None

    @database_sync_to_async
    def _get_role(self, user):
        try:
            return user.profile.role
        except Exception:
            return None

    @database_sync_to_async
    def _get_chat_history(self, session_id):
        from chat.models import ChatSession
        try:
            s = ChatSession.objects.get(session_id=session_id)
            return s.chat_history
        except ChatSession.DoesNotExist:
            return []

    @database_sync_to_async
    def _append_to_history(self, session_id, role, message):
        from chat.models import ChatSession
        try:
            s = ChatSession.objects.get(session_id=session_id)
            s.chat_history.append({'role': role, 'message': message})
            s.save(update_fields=['chat_history'])
        except ChatSession.DoesNotExist:
            pass

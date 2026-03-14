import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

ADMIN_GROUP = 'admin_dashboard'


class AdminDashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the admin live dashboard.
    Admins connect here and receive real-time session updates
    pushed by ChatConsumer whenever a visitor message is processed.
    """

    async def connect(self):
        # Validate JWT token from query string
        token = self._get_token()
        user = await self._authenticate(token)
        if user is None:
            await self.close(code=4001)
            return

        self.user = user
        await self.channel_layer.group_add(ADMIN_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'user'):
            await self.channel_layer.group_discard(ADMIN_GROUP, self.channel_name)

    async def receive(self, text_data):
        # Admins can send a ping to keep the connection alive
        pass

    # ── handlers pushed from ChatConsumer ──────────────────────────────────

    async def session_update(self, event):
        """Forward session update payload to admin browser."""
        await self.send(text_data=json.dumps({
            'type': 'session_update',
            'data': event['data'],
        }))

    async def takeover_ack(self, event):
        """Acknowledge takeover state change to all admin windows."""
        await self.send(text_data=json.dumps({
            'type': 'takeover_ack',
            'data': event['data'],
        }))

    # ── helpers ────────────────────────────────────────────────────────────

    def _get_token(self):
        query_string = self.scope.get('query_string', b'').decode()
        for part in query_string.split('&'):
            if part.startswith('token='):
                return part[len('token='):]
        return None

    @database_sync_to_async
    def _authenticate(self, token):
        if not token:
            return None
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth.models import User
            decoded = AccessToken(token)
            user_id = decoded['user_id']
            return User.objects.get(pk=user_id)
        except Exception:
            return None

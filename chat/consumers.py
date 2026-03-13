import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatSession
from .ai_service import generate_ai_response


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        self.client_id = self.scope['url_route']['kwargs'].get('client_id')
        self.room_group_name = f'chat_{self.session_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        behavior_matrix = data.get('behavior_matrix', {})

        session = await self.get_session(self.client_id, self.session_id)

        # ── Human takeover guard ──────────────────────────────────────────
        # If an admin has taken over, hold the AI response. The admin injects
        # replies manually via GodViewConsumer.receive().
        takeover_active = await database_sync_to_async(
            lambda: session.takeover_active if session else False
        )()

        if takeover_active:
            # Acknowledge receipt to the visitor but do NOT call AI
            await self.send(text_data=json.dumps({
                'type': 'ai_message',
                'message': '...',   # Typing indicator keeps showing until admin sends
            }))
            # Also notify admin group that visitor sent a message
            await self.channel_layer.group_send(
                f"admin_{self.session_id}",
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender': 'user',
                }
            )
            return

        # ── Normal AI response path ───────────────────────────────────────
        ai_response = await database_sync_to_async(generate_ai_response)(
            session, message, behavior_matrix
        )

        # Push AI reply into the session's group so GodView also sees it
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': ai_response.get('reply_text', ''),
                'sender': 'ai',
            }
        )

    # ── Handler: receives messages from the group (from AI or admin inject)
    async def chat_message(self, event):
        sender = event.get('sender', 'ai')
        if sender == 'ai':
            await self.send(text_data=json.dumps({
                'type': 'ai_message',
                'message': event.get('message', ''),
                'suggested_product_id': event.get('suggested_product_id'),
                'admin_injected': event.get('admin_injected', False),
            }))

    @database_sync_to_async
    def get_session(self, client_id, session_id):
        from users.models import Client
        from django.core.exceptions import ValidationError
        import uuid

        try:
            client = Client.objects.get(id=client_id)
        except (Client.DoesNotExist, ValueError, ValidationError):
            client = None

        try:
            if isinstance(session_id, str):
                try:
                    uuid.UUID(session_id)
                except ValueError:
                    return None

            session, _ = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={'client': client, 'visitor_id': session_id}
            )
            return session
        except (ValidationError, ValueError):
            return None

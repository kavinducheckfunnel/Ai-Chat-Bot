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

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        behavior_matrix = data.get('behavior_matrix', {})
        
        session = await self.get_session(self.client_id, self.session_id)
        
        # Generates AI response synchronously in a database_sync_to_async thread
        ai_response = await database_sync_to_async(generate_ai_response)(
            session, message, behavior_matrix
        )
        
        await self.send(text_data=json.dumps({
            'type': 'ai_message',
            'message': ai_response.get('reply_text'),
            'suggested_product_id': ai_response.get('suggested_product_id')
        }))

    @database_sync_to_async
    def get_session(self, client_id, session_id):
        from users.models import Client
        try:
            client = Client.objects.get(id=client_id)
        except (Client.DoesNotExist, ValueError):
            client = None
            
        session, _ = ChatSession.objects.get_or_create(
            session_id=session_id,
            defaults={'client': client}
        )
        return session

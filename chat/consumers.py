import json
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatSession
from .ai_service import generate_ai_response

ADMIN_GROUP = 'admin_dashboard'


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        self.client_id = self.scope['url_route']['kwargs'].get('client_id')
        self.room_group_name = f'chat_{self.session_id}'

        # ── Plan enforcement ─────────────────────────────────────────────
        limit_hit, limit_msg = await self.check_plan_limit(self.client_id)
        if limit_hit:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': limit_msg,
            }))
            await self.close(code=4029)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'message')

        # Handle ping from widget
        if message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return

        message = data.get('message')
        behavior_matrix = data.get('behavior_matrix', {})

        session = await self.get_session(self.client_id, self.session_id)

        # ── God View guard ────────────────────────────────────────────────
        if session.takeover_active:
            # AI is silenced; only admin can send messages via REST endpoint
            await self.send(text_data=json.dumps({
                'type': 'takeover_active',
                'message': 'An admin is currently handling this conversation.',
            }))
            return

        # Update last visitor message time for AFK tracking
        await self.update_visitor_timestamp(session)

        # Generate AI response
        ai_response = await database_sync_to_async(generate_ai_response)(
            session, message, behavior_matrix
        )

        # Send reply to visitor
        await self.send(text_data=json.dumps({
            'type': 'ai_message',
            'message': ai_response.get('reply_text'),
            'suggested_product_id': ai_response.get('suggested_product_id'),
        }))

        # ── Post-response: persist heat score + broadcast to admin ────────
        await self.post_process(session)

    async def post_process(self, session):
        """Persist heat score, check CTA trigger, broadcast to admin dashboard."""
        updated = await self.refresh_and_persist_heat(session)
        if updated:
            await self._broadcast_session_update(updated)
            await self._check_cta_trigger(updated)

    @database_sync_to_async
    def refresh_and_persist_heat(self, session):
        try:
            s = ChatSession.objects.get(session_id=session.session_id)
            score = (
                s.current_intent_ema * 0.45 +
                s.current_budget_ema * 0.30 +
                s.current_urgency_ema * 0.25
            ) * 100
            s.heat_score = round(min(score, 100), 1)
            s.save(update_fields=['heat_score'])
            return s
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def update_visitor_timestamp(self, session):
        ChatSession.objects.filter(session_id=session.session_id).update(
            last_visitor_message_at=timezone.now()
        )

    async def _broadcast_session_update(self, session):
        """Push session update to all connected admin dashboards."""
        payload = {
            'session_id': str(session.session_id),
            'visitor_id': session.visitor_id,
            'heat_score': session.heat_score,
            'conversation_state': session.conversation_state,
            'kanban_state': session.kanban_state,
            'message_count': session.message_count,
            'intent_ema': round(session.current_intent_ema, 3),
            'budget_ema': round(session.current_budget_ema, 3),
            'urgency_ema': round(session.current_urgency_ema, 3),
            'lead_email': session.lead_email,
            'takeover_active': session.takeover_active,
            'client_id': str(session.client_id) if session.client_id else None,
            'updated_at': session.updated_at.isoformat(),
        }
        await self.channel_layer.group_send(ADMIN_GROUP, {
            'type': 'session_update',
            'data': payload,
        })

    @database_sync_to_async
    def _check_cta_trigger(self, session):
        """Fire closing CTA when heat_score >= 75 and not already triggered."""
        if session.heat_score >= 75 and not session.closing_triggered:
            ChatSession.objects.filter(session_id=session.session_id).update(
                closing_triggered=True
            )
            # Enqueue AFK nudge task if not already sent
            from chat.tasks import schedule_afk_nudge
            schedule_afk_nudge.apply_async(
                args=[str(session.session_id)],
                countdown=120,  # 2 min inactivity window
            )

    # ── Handler for admin-injected messages during takeover ──────────────
    async def chat_message(self, event):
        """Relay admin message to visitor WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'ai_message',
            'message': event['message'],
            'source': event.get('source', 'ai'),
        }))

    @database_sync_to_async
    def get_session(self, client_id, session_id):
        from users.models import Client
        try:
            client = Client.objects.get(id=client_id)
        except (Client.DoesNotExist, ValueError, ValidationError):
            client = None

        session, created = ChatSession.objects.get_or_create(
            session_id=session_id,
            defaults={'client': client}
        )
        # Increment monthly counter only on brand-new sessions
        if created and client:
            from users.models import TenantProfile
            TenantProfile.objects.filter(clients=client).update(
                sessions_this_month=models.F('sessions_this_month') + 1
            )
        return session

    @database_sync_to_async
    def check_plan_limit(self, client_id):
        """
        Returns (limit_exceeded: bool, message: str).
        Also fires a warning email when tenant hits 80% of their plan limit.
        """
        from users.models import Client, TenantProfile
        try:
            client = Client.objects.get(id=client_id)
            tenant = TenantProfile.objects.filter(clients=client).select_related('plan').first()
        except (Client.DoesNotExist, ValueError, ValidationError):
            return False, ''

        if not tenant or not tenant.plan:
            return False, ''

        max_s = tenant.plan.max_sessions_per_month
        used = tenant.sessions_this_month

        # Hard limit — block the connection
        if used >= max_s:
            return True, (
                f"Monthly chat limit reached ({max_s} sessions). "
                "Please upgrade your plan to continue."
            )

        # Soft warning at 80% — fire async email if not yet sent
        if used >= int(max_s * 0.8):
            try:
                from users.tasks import send_limit_warning_email
                send_limit_warning_email.delay(tenant.pk)
            except Exception:
                pass

        return False, ''

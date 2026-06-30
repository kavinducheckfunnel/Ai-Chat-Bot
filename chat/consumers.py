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

        # Save visitor IP immediately on connect (server-side, accurate)
        visitor_ip = self._get_client_ip()
        if visitor_ip:
            await self.save_visitor_ip(visitor_ip)

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

        # Handle visitor fingerprint frame — save once, never overwrite
        if message_type == 'visitor_meta':
            await self.save_visitor_meta(data)
            return

        # ── Proactive open trigger (C2) ───────────────────────────────────
        # Fires ~10s after page load when the visitor has not yet opened the
        # chat. Backend builds a behavior-aware question and pushes it back;
        # widget receives source='proactive_open' and auto-opens.
        if message_type == 'proactive_trigger':
            await self.handle_proactive_trigger(data)
            return

        message = data.get('message')
        behavior_matrix = data.get('behavior_matrix', {})
        page_visits = data.get('page_visits', [])
        image_data = data.get('image_data')  # optional base64 image
        # Client-generated id for the visitor's message — lets the sending
        # tab dedupe its own optimistic bubble when the server echoes it back
        # to the whole session group (cross-tab live sync).
        client_msg_id = data.get('msg_id') or ''

        session = await self.get_session(self.client_id, self.session_id)

        # ── Defence-in-depth: drop image_data if the tenant's plan/client
        # has image input turned off. The widget hides the upload button
        # when the feature flag is off, but a hand-crafted WS frame could
        # still slip a payload through. Strip it server-side so untrusted
        # clients can't bypass the flag and force LLM image calls. ─────
        if image_data and not await self._client_allows_image(session):
            import logging as _log
            _log.getLogger(__name__).info(
                f'[ws] image_data stripped — client {session.client_id} '
                f'does not allow image input (plan + toggle both off)'
            )
            image_data = None

        # ── WebSocket rate guard: drop messages within 1 s of the previous ─
        if session.last_visitor_message_at:
            gap = (timezone.now() - session.last_visitor_message_at).total_seconds()
            if gap < 1.0:
                return

        # ── God View guard ────────────────────────────────────────────────
        if session.takeover_active:
            # AI is silenced; only admin can send messages via REST endpoint
            await self.send(text_data=json.dumps({
                'type': 'takeover_active',
                'message': 'An admin is currently handling this conversation.',
            }))
            return

        # ── Cross-tab live sync: echo the visitor's message to the whole
        # session group so any OTHER open tab/device renders it immediately.
        # The sending tab tagged it with `client_msg_id` and already painted
        # it optimistically, so it dedupes on that id and won't double it. ──
        if message:
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'relay_user',
                'message': message,
                'msg_id': client_msg_id,
            })

        # Update last visitor message time for AFK tracking
        await self.update_visitor_timestamp(session)

        # Persist latest page visits and behavioral signals from the widget
        if page_visits:
            await self.save_page_visits(session.session_id, page_visits)
        if behavior_matrix:
            await self.save_behavior_matrix(session.session_id, behavior_matrix)

        # CRITICAL: reload session from DB so generate_ai_response sees the
        # fresh page_visits + behavioral_context. Without this, the AI runs
        # with the stale session loaded BEFORE the writes above and the
        # personalized "Hey, saw you were looking at X" greeting never fires.
        refreshed = await self._refresh_session(session.session_id)
        if refreshed:
            session = refreshed

        # Generate AI response (pass image_data for vision if present)
        ai_response = await database_sync_to_async(generate_ai_response)(
            session, message, behavior_matrix, image_data=image_data
        )

        # Send the AI reply to the whole session GROUP (not just the sending
        # socket) so every open tab/device renders it live. Each AI reply
        # carries a fresh server msg_id so tabs dedupe — including the sending
        # tab, which renders it here exactly once instead of via self.send.
        import uuid as _uuid
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'relay_ai',
            'message': ai_response.get('reply_text'),
            'msg_id': f'ai_{_uuid.uuid4().hex}',
            'suggested_product_id': ai_response.get('suggested_product_id'),
            'quick_replies': ai_response.get('quick_replies') or [],
        })

        # ── Post-response: persist heat score + broadcast to admin ────────
        await self.post_process(session)

    async def relay_user(self, event):
        """Relay a visitor message to every connected tab in the session."""
        await self.send(text_data=json.dumps({
            'type': 'user_message',
            'message': event.get('message', ''),
            'msg_id': event.get('msg_id', ''),
        }))

    async def relay_ai(self, event):
        """Relay an AI reply to every connected tab in the session."""
        await self.send(text_data=json.dumps({
            'type': 'ai_message',
            'message': event.get('message', ''),
            'msg_id': event.get('msg_id', ''),
            'suggested_product_id': event.get('suggested_product_id'),
            'quick_replies': event.get('quick_replies') or [],
        }))

    async def post_process(self, session):
        """Persist heat score, check CTA trigger, broadcast to admin dashboard,
        and prompt the visitor for contact details if the AI just hit
        sales-close conditions but we don't have a lead yet."""
        updated = await self.refresh_and_persist_heat(session)
        if updated:
            await self._broadcast_session_update(updated)
            await self._check_cta_trigger(updated)
            await self._maybe_prompt_lead_capture(updated)

    async def _maybe_prompt_lead_capture(self, session):
        """
        Push a 'lead_capture_required' event to the widget when ALL of:
          • visitor has NOT given a contact yet (neither email NOR phone)
          • EITHER conversation_state is READY_TO_BUY
            OR heat_score >= 75
            OR kanban_state == 'HOT_LEAD'
          • we haven't already prompted in this session (prompted_lead_capture flag)

        The widget listens for this event and opens its lead modal
        automatically. Without this signal, the modal only triggers on
        the visitor's 3rd outbound message, which the QA flagged as
        "contact capture incomplete" — by the time it fires the buying
        moment has passed.
        """
        # A single captured contact (email OR phone) is enough — don't keep
        # prompting once we already have one.
        has_contact = bool((session.lead_email or '').strip() or (session.lead_phone or '').strip())
        if has_contact:
            return
        if getattr(session, 'lead_capture_prompted', False):
            return

        close_state = (session.conversation_state or '').upper() == 'READY_TO_BUY'
        hot_kanban  = (session.kanban_state or '').upper() == 'HOT_LEAD'
        hot_score   = (session.heat_score or 0) >= 75
        if not (close_state or hot_kanban or hot_score):
            return

        # Mark the flag so we don't spam the modal every turn
        await self._set_lead_capture_prompted(session.session_id)

        try:
            await self.send(text_data=json.dumps({
                'type': 'lead_capture_required',
                'reason': 'hot_lead',
                'heat_score': session.heat_score,
            }))
        except Exception:
            pass

    @database_sync_to_async
    def _set_lead_capture_prompted(self, session_id):
        ChatSession.objects.filter(session_id=session_id).update(
            lead_capture_prompted=True,
        )

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
            kanban_fields = ['heat_score']
            # ── Auto-progress the Kanban funnel from live engagement/heat ──
            # NEW → ENGAGED (real back-and-forth) → HOT_LEAD (high heat/intent).
            # CONVERTED is set only on full lead capture; never downgrade past
            # HOT_LEAD / CONVERTED / LOST here.
            cur = (s.kanban_state or 'NEW').upper()
            if cur not in {'CONVERTED', 'HOT_LEAD', 'LOST'}:
                if s.heat_score >= 60 or (s.current_intent_ema or 0) >= 0.6:
                    s.kanban_state = 'HOT_LEAD'
                    kanban_fields.append('kanban_state')
                elif cur == 'NEW' and (s.message_count or 0) >= 2:
                    s.kanban_state = 'ENGAGED'
                    kanban_fields.append('kanban_state')
            s.save(update_fields=kanban_fields)

            # Update Visitor's latest known EMA + carry lead info up.
            # Lifetime totals are computed at query time via Sum() across the
            # visitor's sessions — keeps writes cheap and avoids drift.
            if s.visitor_obj_id:
                from .models import Visitor
                v_update = {
                    'intent_ema': s.current_intent_ema,
                    'budget_ema': s.current_budget_ema,
                    'urgency_ema': s.current_urgency_ema,
                }
                if s.lead_email:
                    v_update['lead_email'] = s.lead_email
                if s.lead_phone:
                    v_update['lead_phone'] = s.lead_phone
                Visitor.objects.filter(pk=s.visitor_obj_id).update(**v_update)
            return s
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def update_visitor_timestamp(self, session):
        ChatSession.objects.filter(session_id=session.session_id).update(
            last_visitor_message_at=timezone.now()
        )

    async def handle_proactive_trigger(self, data):
        """Fires ~10s after page load. Send a behavior-aware question and
        auto-open the widget.

        Cooldown guards (C4):
        - once per session (proactive_open_sent flag in behavioral_context)
        - skip if any nudge has fired in the last 60s (last_nudge_at)
        - skip if visitor already sent a message (they don't need a nudge)
        - respect tenant cta_mode (skip if 'off')
        """
        session = await self.get_session(self.client_id, self.session_id)

        # Save the latest behavior frame so the LLM has fresh context
        behavior_matrix = data.get('behavior_matrix') or {}
        page_visits = data.get('page_visits') or []
        if page_visits:
            await self.save_page_visits(session.session_id, page_visits)
        if behavior_matrix:
            await self.save_behavior_matrix(session.session_id, behavior_matrix)
        session = await self._refresh_session(session.session_id) or session

        if await self._proactive_should_skip(session):
            return

        # Build a context-aware question via LLM (re-uses _generate_personalised_cta)
        from chat.views import _generate_personalised_cta
        client = session.client
        text = await database_sync_to_async(_generate_personalised_cta)(
            session, client, 'proactive_open'
        )
        if not text:
            # No browsing context → fall back to brand-aware template
            brand = (client.name if client else 'us')
            text = f"👋 Welcome to {brand}! What brings you in today — anything I can point you toward?"

        await self._persist_proactive_message(session, text)
        await self.send(text_data=json.dumps({
            'type': 'ai_message',
            'message': text,
            'source': 'proactive_open',
        }))

    @database_sync_to_async
    def _proactive_should_skip(self, session):
        if not session or not session.client:
            return True
        # Respect tenant cta_mode
        if getattr(session.client, 'cta_mode', 'ai') == 'off':
            return True
        # Already fired this session
        ctx = session.behavioral_context or {}
        if ctx.get('proactive_open_sent'):
            return True
        # Visitor already chatted — they don't need a nudge
        if session.message_count and session.message_count > 0:
            return True
        # Global 60s nudge cooldown (C4): suppress overlap with other triggers
        if session.last_nudge_at:
            from datetime import timedelta
            if (timezone.now() - session.last_nudge_at) < timedelta(seconds=60):
                return True
        return False

    @database_sync_to_async
    def _persist_proactive_message(self, session, text):
        """Append the proactive message to history + set sent flag + nudge_at."""
        history = session.chat_history or []
        history.append({'role': 'ai', 'message': text, 'source': 'proactive_open'})
        ctx = session.behavioral_context or {}
        ctx['proactive_open_sent'] = True
        ChatSession.objects.filter(session_id=session.session_id).update(
            chat_history=history,
            behavioral_context=ctx,
            last_nudge_at=timezone.now(),
            last_message_at=timezone.now(),
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
        """Relay admin message (and any media attachments) to visitor WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'ai_message',
            'message': event['message'],
            'source': event.get('source', 'ai'),
            'attachments': event.get('attachments', []),
        }))

    def _get_client_ip(self):
        """Extract real client IP from ASGI scope headers (respects X-Forwarded-For)."""
        headers = dict(self.scope.get('headers', []))
        forwarded = headers.get(b'x-forwarded-for', b'').decode()
        if forwarded:
            return forwarded.split(',')[0].strip()
        client = self.scope.get('client')
        if client:
            return client[0]
        return None

    @database_sync_to_async
    def save_visitor_ip(self, ip):
        """Save IP on connect — only if not already recorded."""
        ChatSession.objects.filter(
            session_id=self.session_id,
            visitor_ip__isnull=True,
        ).update(visitor_ip=ip)

    @database_sync_to_async
    def _refresh_session(self, session_id):
        """Reload session from DB so in-memory copy reflects writes from
        save_page_visits / save_behavior_matrix / save_visitor_meta. Without
        this, generate_ai_response() reads stale fields and personalization
        can't fire even when the data has been persisted."""
        return ChatSession.objects.filter(session_id=session_id).select_related('client').first()

    @database_sync_to_async
    def save_visitor_meta(self, data):
        """
        Save visitor fingerprint + accumulated page_visits.

        Identity fields (country, device, OS, browser, etc.) only fill when
        null — they don't change for a visitor mid-session.

        page_visits must ALWAYS overwrite to the latest snapshot, because
        the widget accumulates pages across navigations and resends the full
        list on every WebSocket open. Without this, the AI only ever sees
        page_visits from the very first save and misses everything after.

        ── ORDER MATTERS ────────────────────────────────────────────────
        visitor_meta fires on WebSocket open — BEFORE any chat message —
        so the ChatSession typically doesn't exist yet on the first connect.
        We must ENSURE the session exists FIRST, otherwise the page_visits
        UPDATE silently no-ops and we lose every page the visitor browsed
        before they chatted. This was the "only last page in heatmap" bug:
        Page A's visit was sent, the session didn't exist, the update did
        nothing, the session was created later with empty page_visits.
        """
        page_visits = data.get('page_visits') or []
        visitor_uid = (data.get('visitor_uid') or '').strip()[:64]

        # ── 1. Resolve the client from the URL (authoritative) ───────────
        from users.models import Client
        client = None
        if self.client_id:
            try:
                client = Client.objects.get(id=self.client_id)
            except (Client.DoesNotExist, ValueError, ValidationError):
                client = None

        # ── 2. Ensure the ChatSession exists BEFORE we touch its fields ──
        # Seed with the page_visits we already have so even a one-page
        # visitor who never chats still leaves a footprint.
        if client:
            ChatSession.objects.get_or_create(
                session_id=self.session_id,
                defaults={'client': client, 'page_visits': page_visits},
            )

        # ── 3. Identity: only fill nulls (first save) ────────────────────
        identity_update = {}
        identity_map = {
            'country': 'visitor_country',
            'city': 'visitor_city',
            'country_code': 'visitor_country_code',
            'device': 'visitor_device',
            'os': 'visitor_os',
            'browser': 'visitor_browser',
            'referrer': 'visitor_referrer',
            'timezone': 'visitor_timezone',
        }
        for key, field in identity_map.items():
            val = data.get(key)
            if val:
                identity_update[field] = val

        if identity_update:
            ChatSession.objects.filter(
                session_id=self.session_id,
                visitor_country__isnull=True,
            ).update(**identity_update)

        # ── 4. page_visits — always overwrite with latest snapshot ───────
        if page_visits:
            ChatSession.objects.filter(session_id=self.session_id).update(
                page_visits=page_visits
            )

        # ── 5. Upsert persistent Visitor record + link to session ────────
        if visitor_uid and client:
            from .models import Visitor

            visitor, _ = Visitor.objects.get_or_create(
                visitor_uid=visitor_uid,
                client=client,
                defaults={
                    'device': data.get('device') or '',
                    'os': data.get('os') or '',
                    'browser': data.get('browser') or '',
                    'country': data.get('country') or '',
                    'city': data.get('city') or '',
                    'country_code': data.get('country_code') or '',
                    'timezone': data.get('timezone') or '',
                    'ip': data.get('ip') or '',
                },
            )

            session = ChatSession.objects.filter(session_id=self.session_id).first()
            if session and session.visitor_obj_id != visitor.id:
                session.visitor_obj = visitor
                session.save(update_fields=['visitor_obj'])
                Visitor.objects.filter(pk=visitor.pk).update(
                    total_sessions=models.F('total_sessions') + 1,
                )

    @database_sync_to_async
    def save_page_visits(self, session_id, page_visits):
        """Merge incoming page_visits with the accumulated server-side list.

        Why merge instead of overwrite: when the visitor navigates across
        multiple pages with full reloads, the widget tracker resets its
        in-memory pageVisits to [] each load. Without merging, the LATEST
        send would clobber earlier pages, making the bot blind to the
        visitor's journey. Pages 1-2 would be lost the moment page 3
        sent its snapshot.

        Dedup key: (url, visited_at). Keeps the most-recent 30 entries
        so the JSON column stays bounded.
        """
        if not page_visits:
            return
        try:
            existing = list(ChatSession.objects.filter(session_id=session_id).values_list('page_visits', flat=True))[0] or []
        except IndexError:
            return
        if not isinstance(existing, list):
            existing = []

        # Dedup by (url, visited_at). Incoming entries replace existing ones
        # with the same key so we get the latest duration_seconds for each
        # page (visitor returning to a page → longer dwell).
        seen = {}
        for entry in existing + list(page_visits):
            if not isinstance(entry, dict):
                continue
            key = (entry.get('url', ''), entry.get('visited_at', ''))
            seen[key] = entry

        merged = sorted(seen.values(), key=lambda e: e.get('visited_at', ''))[-30:]
        ChatSession.objects.filter(session_id=session_id).update(page_visits=merged)

    @database_sync_to_async
    def save_behavior_matrix(self, session_id, behavior_matrix):
        """
        Persist the FULL behavioral signal set + nudge EMA scores.

        Delegates to analytics.views._apply_behavior so the consumer path
        uses the same rich pipeline as the beacon endpoint. Previously this
        only saved 5 fields and ignored: click_count, cta_clicks, rage_clicks,
        add_to_cart_clicks, form_focused, copy_events, price_views, etc. —
        all of which feed the hot-signals UI and EMA scoring.
        """
        if not behavior_matrix:
            return
        session = ChatSession.objects.filter(session_id=session_id).first()
        if not session:
            return
        try:
            from analytics.views import _apply_behavior
            _apply_behavior(session, behavior_matrix)
        except Exception:
            # Fall back to the legacy minimal save so the chat never blocks
            ctx = session.behavioral_context or {}
            ctx['pages_viewed']          = len(behavior_matrix.get('pagesViewed', []))
            ctx['pricing_page_visits']   = behavior_matrix.get('pricingPageVisits', 0)
            ctx['exit_intent_triggered'] = behavior_matrix.get('exitIntentFired', False)
            ctx['scroll_depth']          = behavior_matrix.get('scrollDepth', 0)
            ctx['time_on_site']          = behavior_matrix.get('timeOnSite', 0)
            session.behavioral_context = ctx
            session.save(update_fields=['behavioral_context'])

    @database_sync_to_async
    def _client_allows_image(self, session):
        """Is image upload allowed for this session's client?

        Auto-enabled per plan: any tenant whose plan includes image input
        (Growth and up) gets it without flipping the per-client toggle. The
        explicit client toggle still works as an override for plans that
        don't include it (e.g. a one-off grant on Starter).

        Takes the SESSION (not session.client) so the FK + plan lookups run
        inside this sync DB context — touching session.client from the async
        receive() coroutine triggers a lazy query and SynchronousOnlyOperation.
        """
        from .utils import client_allows_image
        return client_allows_image(session.client)

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

        # ── Cross-tenant safety: URL is authoritative ─────────────────────────
        # If the existing session is bound to a DIFFERENT client than the URL,
        # this is a stale session_id reused under a new embed code (developer
        # testing, or sessionStorage carry-over from a prior tenant). Rebind
        # the session to the URL's client and wipe any tenant-specific state
        # so we never leak chat history / chunks / EMA across tenants.
        if not created and client and session.client_id != client.id:
            import logging as _log
            _log.warning(
                f'[consumers] session {session_id} tenant mismatch: '
                f'db={session.client_id} url={client.id} — rebinding to URL client'
            )
            session.client = client
            session.chat_history = []
            session.page_visits = []
            session.behavioral_context = {}
            session.current_intent_ema = 0.0
            session.current_budget_ema = 0.0
            session.current_urgency_ema = 0.0
            session.previous_intent_ema = 0.0
            session.previous_budget_ema = 0.0
            session.previous_urgency_ema = 0.0
            session.message_count = 0
            session.heat_score = 0.0
            session.lead_email = ''
            session.lead_phone = ''
            session.save()

        # Increment monthly counter only on brand-new sessions
        if created and client:
            from users.models import TenantProfile
            TenantProfile.objects.filter(clients=client).update(
                sessions_this_month=models.F('sessions_this_month') + 1
            )
            # Apply any beacon data cached before the session existed
            from django.core.cache import cache
            from analytics.views import _apply_behavior
            cached_behavior = cache.get(f'beacon_{session_id}')
            if cached_behavior:
                _apply_behavior(session, cached_behavior)
                cache.delete(f'beacon_{session_id}')
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

        # -1 means unlimited — never block
        if max_s < 0:
            return False, ''

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

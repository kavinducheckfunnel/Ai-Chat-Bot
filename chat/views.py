import logging
import uuid
import requests as http_requests
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import ChatSession
from .ai_service import generate_ai_response
from .throttles import ChatRateThrottle, SessionRateThrottle
from users.models import Client
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def _get_tenant_for_client(client):
    """Find the TenantProfile that owns this client."""
    from users.models import TenantProfile
    return TenantProfile.objects.filter(clients=client).first()


def _check_and_increment_message(tenant) -> bool:
    """Check message quota; atomically increment if within limit. Returns False if quota exceeded."""
    if not tenant or not tenant.plan:
        return True
    from users.feature_flags import _effective_limit
    limit = _effective_limit(tenant.plan.max_messages_per_month, tenant.addon_messages)
    if limit >= 0 and tenant.messages_this_month >= limit:
        return False
    from django.db.models import F
    from users.models import TenantProfile
    TenantProfile.objects.filter(pk=tenant.pk).update(messages_this_month=F('messages_this_month') + 1)
    return True


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ChatRateThrottle, SessionRateThrottle])
def chat_message(request):
    session_id = request.data.get('session_id')
    message = request.data.get('message')
    behavior_matrix = request.data.get('behavior_matrix', {})
    image_data = request.data.get('image_data')

    if not session_id:
        return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    # Image-only messages are allowed (visitor sends a screenshot with no
    # caption). For text-only flows we still require `message`.
    if not message and not image_data:
        return Response({'error': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)

    session, _ = ChatSession.objects.get_or_create(session_id=session_id)

    # Mirror the WS guard: drop image_data if the tenant turned off
    # image_input_enabled. Widget hides the upload control, but the REST
    # endpoint is reachable from any HTTP client.
    if image_data and session.client and not session.client.image_input_enabled:
        image_data = None

    tenant = _get_tenant_for_client(session.client) if session.client else None
    if not _check_and_increment_message(tenant):
        return Response({
            'error': 'quota_exceeded',
            'reply_text': "I'm sorry, this chatbot has reached its monthly message limit. Please try again next month.",
        }, status=status.HTTP_200_OK)  # 200 so widget still renders the message

    ai_response = generate_ai_response(
        session, message or '', behavior_matrix, image_data=image_data,
    )
    return Response(ai_response)


@api_view(['GET'])
@permission_classes([AllowAny])
def widget_config(request, client_id):
    """
    Public endpoint — returns branding config for a given client.
    Called by the chat widget on load to apply client-specific colours and name.
    """
    try:
        client = Client.objects.get(pk=client_id, is_active=True)
    except (Client.DoesNotExist, Exception):
        # Return sensible defaults so the widget still loads
        return Response({
            'chatbot_name': 'AI Assistant',
            'chatbot_color': '#3B82F6',
            'chatbot_theme': 'dark',
            'chatbot_logo_url': None,
            'cta_message': "You're clearly ready — grab your exclusive discount:",
            'fomo_offer_text': None,
            'fomo_countdown_seconds': 600,
            'discount_code': None,
        })

    return Response({
        'chatbot_name': client.chatbot_name,
        'chatbot_color': client.chatbot_color,
        'chatbot_theme': client.chatbot_theme,
        'chatbot_logo_url': client.chatbot_logo_url,
        'cta_message': client.cta_message,
        'fomo_offer_text': client.fomo_offer_text,
        'fomo_countdown_seconds': client.fomo_countdown_seconds,
        'discount_code': client.discount_code,
        'voice_input_enabled': client.voice_input_enabled,
        'image_input_enabled': client.image_input_enabled,
    })


def _generate_personalised_cta(session, client, trigger_type):
    """
    Build a tailor-made CTA message via the LLM, reflecting what THIS specific
    visitor was looking at when the trigger fired. Returns None if the visitor
    has no meaningful browsing context (falls back to the static template).

    Cached per (session, trigger_type) for 5 min — re-fires within that window
    reuse the cached message instead of calling the LLM again. This keeps cost
    bounded while still feeling personal.
    """
    if not client or not session:
        return None
    try:
        from django.core.cache import cache
        cache_key = f'cta_{session.session_id}_{trigger_type}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        from chat.ai_service import build_browsing_context, _build_llm
        from langchain_core.messages import SystemMessage, HumanMessage

        ctx = build_browsing_context(session)
        # Need a real interest hook for personalisation to be meaningful
        if not ctx.get('top_interest') and not ctx.get('signals'):
            return None

        # Compose a tight, one-shot LLM prompt
        pages_summary = ', '.join(
            f"{p['title']} ({p['dwell_seconds']}s)"
            for p in (ctx.get('pages') or [])[-5:]
        ) or 'general browsing'
        signals_summary = '; '.join(ctx.get('signals') or []) or 'none'
        top = ctx.get('top_interest') or 'a product'

        trigger_intent = {
            'exit_intent': 'they are about to leave the site',
            'pricing_hesitation': 'they have visited pricing multiple times without acting',
            'abandoned_form': 'they started filling a form but stopped',
            'deep_engagement': 'they have engaged deeply (long time, deep scroll)',
            'high_intent_action': 'they have shown strong intent signals',
            'add_to_cart_help': 'they just added something to cart',
            'rage_click_help': 'they are showing signs of frustration',
            'proactive_open': 'this is the very first proactive contact — '
                              'visitor has been browsing ~10 seconds, has not '
                              'opened chat yet. Open with a warm one-liner '
                              'referencing what they were looking at and end '
                              'with a single discovery question (NOT a hard sell). '
                              'Match the channel: web visitor, brief and friendly.',
        }.get(trigger_type, 'they need a nudge')

        discount_hint = (
            f"Available discount code: {client.discount_code}." if client.discount_code else ''
        )

        system_prompt = (
            "You are writing a single short CTA chat message (1 sentence, max 25 words, "
            "max 150 characters). It must reference what the visitor was JUST looking at "
            "and gently nudge them. Sound human and warm, never pushy. No emojis except "
            "one optional at the end. Return ONLY the message text — no quotes, no preamble."
        )
        user_prompt = (
            f"Website: {client.domain_url or client.name}\n"
            f"Visitor's primary interest: {top}\n"
            f"Recent pages: {pages_summary}\n"
            f"Behavioral signals: {signals_summary}\n"
            f"Intent heat: {ctx.get('heat_level', 'LOW')}\n"
            f"Trigger context: {trigger_intent}\n"
            f"{discount_hint}\n\n"
            f"Write the CTA message now."
        )

        llm, _ = _build_llm(client)
        result = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        text = result.content if hasattr(result, 'content') else str(result)
        text = text.strip().strip('"').strip("'").strip()
        if not text or len(text) > 280:
            return None

        cache.set(cache_key, text, 300)  # 5 min
        return text
    except Exception as e:
        logger.warning(f'[trigger] personalised CTA failed: {e}')
        return None


@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_event(request):
    """
    Called by the widget when a FOMO trigger fires (exit-intent or pricing hesitation).
    Pushes a FOMO message into the visitor's open WebSocket if the client has one configured.

    Body: { session_id, client_id, trigger_type: 'exit_intent' | 'pricing_hesitation' }
    """
    session_id = request.data.get('session_id')
    client_id = request.data.get('client_id')
    trigger_type = request.data.get('trigger_type', 'exit_intent')

    if not session_id:
        return Response({'error': 'session_id required'}, status=status.HTTP_400_BAD_REQUEST)

    # Look up session
    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except (ChatSession.DoesNotExist, Exception):
        return Response({'status': 'ignored', 'reason': 'session not found'})

    # Don't fire during admin takeover
    if session.takeover_active:
        return Response({'status': 'ignored', 'reason': 'takeover active'})

    # Don't fire if already triggered
    if session.closing_triggered:
        return Response({'status': 'ignored', 'reason': 'already triggered'})

    client = session.client
    if not client:
        return Response({'status': 'ignored', 'reason': 'no client'})

    # ── Respect tenant's CTA strategy ────────────────────────────────────
    # cta_mode picks ONE follow-up flow so we never send both an AI-generated
    # behavior trigger AND a manual AFK nudge for the same visitor.
    #   'ai'     → fire behavior CTA here AND also via AFK nudge
    #   'manual' → skip behavior CTA; AFK nudge will send the saved text
    #   'off'    → skip all CTAs
    if getattr(client, 'cta_mode', 'ai') != 'ai':
        return Response({'status': 'ignored', 'reason': f'cta_mode={client.cta_mode}'})

    # ── Try LLM-generated personalised CTA first ─────────────────────────
    # If the visitor has clear browsing context (top interest + EMA signals),
    # ask the LLM for a tailor-made CTA referencing what THEY specifically
    # were doing. Falls through to the static template below on any failure.
    personalised_msg = _generate_personalised_cta(session, client, trigger_type)
    if personalised_msg:
        fomo_msg = personalised_msg
    elif trigger_type == 'exit_intent':
        fomo_msg = (
            client.fomo_offer_text
            or (
                f"Wait! Before you go — use code **{client.discount_code}** for an exclusive discount!"
                if client.discount_code
                else "Wait! Don't leave yet — I can help you find exactly what you're looking for."
            )
        )
    elif trigger_type == 'pricing_hesitation':
        fomo_msg = (
            client.fomo_offer_text
            or (
                f"Still deciding? Use code **{client.discount_code}** — limited time only!"
                if client.discount_code
                else "Still deciding? I can walk you through our plans and find the best fit for you."
            )
        )
    elif trigger_type == 'add_to_cart_help':
        fomo_msg = "Great choice! Do you have any questions about this product before you check out? I'm here to help. 🛒"
    elif trigger_type == 'abandoned_form':
        fomo_msg = "Looks like you started filling something out — can I help you complete it or answer any questions?"
    elif trigger_type == 'deep_engagement':
        fomo_msg = "You've been exploring thoroughly! Is there anything specific I can help you find or decide on? 💬"
    elif trigger_type == 'rage_click_help':
        fomo_msg = "Looks like something might not be working as expected — can I help you find what you're looking for?"
    elif trigger_type == 'high_intent_action':
        fomo_msg = (
            f"You seem ready to take the next step! Use code **{client.discount_code}** for an exclusive deal."
            if client.discount_code
            else "You seem really interested — I'd love to help you take the next step. What questions do you have?"
        )
    else:
        fomo_msg = "Hey! I noticed you've been exploring — can I help you with anything? 💬"

    # Countdown hint only when:
    #   1) this is a closing-type trigger
    #   2) there's an actual offer attached (discount_code OR fomo_offer_text)
    #   3) the countdown is >= 60s so "expires in 0 minutes" never appears
    # Without a real offer the urgency phrasing reads as fake — that's the
    # "This offer expires in 0 minutes!" garbage the user reported.
    CLOSING_TRIGGERS = {'exit_intent', 'pricing_hesitation', 'high_intent_action'}
    has_offer = bool(client.discount_code or client.fomo_offer_text)
    seconds = client.fomo_countdown_seconds or 0
    if trigger_type in CLOSING_TRIGGERS and has_offer and seconds >= 60:
        mins = seconds // 60
        fomo_msg += f" This offer expires in {mins} minute{'s' if mins != 1 else ''}!"

    # Persist to chat history; only mark closing_triggered for exit/pricing/high-intent
    history = session.chat_history or []
    history.append({'role': 'ai', 'message': fomo_msg, 'source': trigger_type})
    update_fields = {'chat_history': history}
    if trigger_type in CLOSING_TRIGGERS:
        update_fields['closing_triggered'] = True
    ChatSession.objects.filter(session_id=session_id).update(**update_fields)

    # Push into visitor's WebSocket
    channel_layer = get_channel_layer()
    group_name = f'chat_{session_id}'
    try:
        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'chat_message',
            'message': fomo_msg,
            'source': trigger_type,
        })
    except Exception:
        pass  # WS might not be open; message is still saved to history

    return Response({'status': 'sent', 'trigger_type': trigger_type})


@api_view(['POST'])
@permission_classes([AllowAny])
def capture_lead(request):
    """
    Called by the widget lead-capture modal to save visitor email/phone to
    the session.

    Sales-enablement upgrades on top of the original save:
      • Auto-promotes kanban_state → HOT_LEAD if heat or intent crossed the
        threshold by the time the modal closes (the visitor providing
        contact mid-conversation is itself a strong buying signal).
      • Pushes an AI confirmation message into the chat ("Got it, our team
        will reach you within X hours about <product>") so the visitor
        sees the lead was captured — the QA report flagged "contact
        capture is incomplete" because there was no visible confirmation.
      • Broadcasts a session_update over the admin_dashboard channel so
        the Kanban + Inbox refresh live without a reload.

    Body: { session_id, email, phone? }
    """
    session_id = request.data.get('session_id')
    email = (request.data.get('email') or '').strip()

    if not session_id or not email:
        return Response({'error': 'session_id and email required'}, status=status.HTTP_400_BAD_REQUEST)

    phone = (request.data.get('phone') or '').strip()

    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': 'session not found'}, status=status.HTTP_404_NOT_FOUND)

    # ── Phone validation + normalisation (Sri Lankan +94 standard) ─────────
    # Reject malformed numbers up front so the CRM never fills with junk like
    # "12345" or "call me later". Valid inputs (0771234567, 771234567,
    # +94771234567, with spaces/dashes) all normalise to +94771234567.
    if phone:
        from chat.phone_utils import normalize_phone
        country = getattr(session.client, 'lead_country', None) or 'LK'
        normalized, ok = normalize_phone(phone, country=country)
        if not ok:
            return Response(
                {'error': 'invalid_phone',
                 'detail': 'Please enter a valid Sri Lankan mobile number (e.g. +94 77 123 4567).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phone = normalized

    session.lead_email = email
    if phone:
        session.lead_phone = phone

    # ── Auto-promote to HOT_LEAD on lead capture when intent/heat is high ──
    # Receiving the contact info itself is a strong intent signal — combined
    # with EMA we promote so the tenant sees the right column on the Kanban
    # without manual triage.
    promoted = False
    heat = session.heat_score or 0
    intent = session.current_intent_ema or 0
    if (heat >= 60 or intent >= 0.6) and (session.kanban_state or '').upper() in {'NEW', 'CONTACTED', 'QUALIFIED'}:
        session.kanban_state = 'HOT_LEAD'
        promoted = True

    # ── Inject an in-chat confirmation so the visitor sees the lead saved ──
    # Phrased to acknowledge urgency context when it's there, otherwise a
    # plain "we'll be in touch" line. The 24h window is a safe default —
    # tenants can override via client.sla_response_hours in a future migration.
    top_interest = ''
    try:
        from chat.ai_service import build_browsing_context
        bs = build_browsing_context(session)
        top_interest = (bs or {}).get('top_interest', '') or ''
    except Exception:
        pass

    urgent = (session.current_urgency_ema or 0) >= 0.7
    if urgent and top_interest:
        confirm_text = (
            f"Got it — I've marked you as a priority lead for the {top_interest}. "
            f"Our team will reach out shortly to confirm delivery details."
        )
    elif urgent:
        confirm_text = (
            "Got it — I've marked this as a priority lead. "
            "Our team will reach out shortly to confirm delivery details."
        )
    elif top_interest:
        confirm_text = (
            f"Thanks! Your details are saved. Our team will reach out within "
            f"24 hours about the {top_interest}."
        )
    else:
        confirm_text = (
            "Thanks! Your details are saved. Our team will be in touch within 24 hours."
        )

    history = session.chat_history or []
    history.append({'role': 'ai', 'message': confirm_text, 'source': 'lead_captured'})
    session.chat_history = history

    session.save(update_fields=[
        'lead_email', 'lead_phone', 'kanban_state', 'chat_history', 'updated_at',
    ])

    client = session.client

    # ── Push the confirmation into the visitor's WebSocket ────────────────
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(f'chat_{session_id}', {
            'type': 'chat_message',
            'message': confirm_text,
            'source': 'lead_captured',
        })
    except Exception:
        pass  # widget might be closed — message is still in chat_history

    # ── Broadcast session_update so admin dashboards refresh live ─────────
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)('admin_dashboard', {
            'type': 'session_update',
            'data': {
                'session_id': str(session.session_id),
                'visitor_id': session.visitor_id,
                'heat_score': session.heat_score,
                'conversation_state': session.conversation_state,
                'kanban_state': session.kanban_state,
                'message_count': session.message_count,
                'lead_email': session.lead_email,
                'lead_phone': session.lead_phone,
                'takeover_active': session.takeover_active,
                'client_id': str(session.client_id) if session.client_id else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
            },
        })
    except Exception:
        pass

    # ── Outbound integrations (Slack + tenant webhook + HubSpot) ──────────
    if client:
        try:
            from chat.utils import fire_slack_notification, fire_outbound_webhook
            badge = ':fire: HOT LEAD' if promoted or (session.kanban_state == 'HOT_LEAD') else ':mega: Lead captured'
            slack_text = (
                f'{badge} on *{client.name}*\n'
                f'Email: {email}' + (f' · Phone: {phone}' if phone else '')
                + (f'\nProduct interest: {top_interest}' if top_interest else '')
            )
            fire_slack_notification(client, slack_text)
            fire_outbound_webhook(client, 'lead_captured', {
                'session_id': str(session_id),
                'visitor_id': session.visitor_id,
                'lead_email': email,
                'lead_phone': phone or '',
                'kanban_state': session.kanban_state,
                'heat_score': session.heat_score,
                'top_interest': top_interest,
            })
        except Exception:
            pass

    # Fire HubSpot sync asynchronously if the client has integration configured
    try:
        from users.tasks import sync_lead_to_hubspot
        sync_lead_to_hubspot.delay(str(session_id))
    except Exception:
        pass

    return Response({
        'status': 'saved',
        'kanban_state': session.kanban_state,
        'is_hot_lead': session.kanban_state == 'HOT_LEAD',
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, product_id):
    """
    Returns product data for a given product_id by looking up DocumentChunks.
    Called by the ProductCard widget component.
    """
    from scraper.models import DocumentChunk
    import re

    chunks = DocumentChunk.objects.filter(product_id=str(product_id)).order_by('id')[:3]
    if not chunks:
        return Response({'error': 'product not found'}, status=status.HTTP_404_NOT_FOUND)

    chunk = chunks[0]
    meta = chunk.metadata or {}

    price = meta.get('price') or meta.get('regular_price')
    if not price:
        match = re.search(r'\$[\d,]+(?:\.\d{2})?', chunk.content)
        price = match.group(0) if match else None

    title = meta.get('title') or meta.get('name') or chunk.content.split('\n')[0][:80]

    lines = [l.strip() for l in chunk.content.split('\n') if l.strip()]
    description = lines[1] if len(lines) > 1 else (lines[0][:160] if lines else '')

    # Build cart URL based on platform
    cart_url = None
    source_url = chunk.source_url or ''
    platform = meta.get('platform', '').lower()

    if platform == 'shopify' or '/products/' in source_url:
        # Shopify: /cart/<variant_id>:1 — use product_id as variant_id
        try:
            from urllib.parse import urlparse
            parsed = urlparse(source_url)
            base = f'{parsed.scheme}://{parsed.netloc}'
            cart_url = f'{base}/cart/{product_id}:1'
        except Exception:
            pass
    elif platform == 'woocommerce' or 'woocommerce' in meta.get('type', '').lower():
        cart_url = f'{source_url}?add-to-cart={product_id}'
    elif source_url:
        # WordPress/generic: best effort — link directly to the product page
        cart_url = source_url

    return Response({
        'product_id': product_id,
        'title': title,
        'price': price,
        'description': description[:200],
        'url': chunk.source_url,
        'cart_url': cart_url,
        'image_url': meta.get('image_url') or meta.get('image'),
    })


# ─── WhatsApp Business webhook ────────────────────────────────────────────────

def _get_or_create_channel_session(client, visitor_id, channel):
    """Get the most recent open session (within 24 h) for a channel visitor, or create one."""
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=24)
    session = (
        ChatSession.objects.filter(
            client=client,
            visitor_id=visitor_id,
            channel=channel,
            created_at__gte=cutoff,
        )
        .order_by('-created_at')
        .first()
    )
    if not session:
        session = ChatSession.objects.create(
            client=client,
            visitor_id=visitor_id,
            channel=channel,
        )
    return session


def _send_whatsapp_reply(phone_number_id, access_token, to, text):
    try:
        http_requests.post(
            f'https://graph.facebook.com/v20.0/{phone_number_id}/messages',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            json={
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'text',
                'text': {'body': text},
            },
            timeout=10,
        )
    except Exception as e:
        logger.error(f'[whatsapp_reply] Failed: {e}')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def whatsapp_webhook(request, client_id):
    try:
        client = Client.objects.get(pk=client_id)
    except (Client.DoesNotExist, Exception):
        return HttpResponse('Not found', status=404)

    # ── Webhook verification (GET) ────────────────────────────────────────
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if mode == 'subscribe' and token == client.whatsapp_verify_token:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('Forbidden', status=403)

    # ── Incoming message (POST) ───────────────────────────────────────────
    data = request.data
    try:
        entry = data['entry'][0]
        change = entry['changes'][0]['value']
        messages = change.get('messages', [])
        if not messages:
            return HttpResponse('OK')  # delivery receipt / read receipt

        msg = messages[0]
        if msg.get('type') != 'text':
            return HttpResponse('OK')  # ignore media for now

        sender_phone = msg['from']
        text = msg['text']['body']
    except (KeyError, IndexError):
        return HttpResponse('OK')

    if not client.whatsapp_phone_number_id or not client.whatsapp_access_token:
        return HttpResponse('Channel not configured', status=400)

    # Route through AI
    session = _get_or_create_channel_session(client, sender_phone, 'whatsapp')
    tenant = _get_tenant_for_client(client)
    if not _check_and_increment_message(tenant):
        return HttpResponse('OK')  # quota exceeded — silently skip
    try:
        result = generate_ai_response(session, text, {})
        reply_text = result.get('reply_text', 'Sorry, I could not process your request.')
    except Exception as e:
        logger.error(f'[whatsapp_webhook] AI error: {e}')
        reply_text = 'Sorry, something went wrong on my end.'

    _send_whatsapp_reply(
        client.whatsapp_phone_number_id,
        client.whatsapp_access_token,
        sender_phone,
        reply_text,
    )
    return HttpResponse('OK')


# ─── Facebook Messenger webhook ───────────────────────────────────────────────

def _send_messenger_reply(page_access_token, recipient_id, text):
    try:
        resp = http_requests.post(
            'https://graph.facebook.com/v20.0/me/messages',
            params={'access_token': page_access_token},
            json={
                'recipient': {'id': recipient_id},
                'message': {'text': text},
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(f'[messenger_reply] Graph API error {resp.status_code}: {resp.text}')
        else:
            logger.info(f'[messenger_reply] Sent OK to {recipient_id}')
    except Exception as e:
        logger.error(f'[messenger_reply] Failed: {e}')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def messenger_webhook(request, client_id):
    try:
        client = Client.objects.get(pk=client_id)
    except (Client.DoesNotExist, Exception):
        return HttpResponse('Not found', status=404)

    # ── Webhook verification (GET) ────────────────────────────────────────
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if mode == 'subscribe' and token == client.messenger_verify_token:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('Forbidden', status=403)

    # ── Incoming message (POST) ───────────────────────────────────────────
    data = request.data
    try:
        entry = data['entry'][0]
        messaging = entry['messaging'][0]
        sender_psid = messaging['sender']['id']
        msg = messaging.get('message', {})
        text = msg.get('text')
        if not text:
            return HttpResponse('OK')  # sticker / attachment — ignore
    except (KeyError, IndexError):
        return HttpResponse('OK')

    if not client.messenger_page_access_token:
        return HttpResponse('Channel not configured', status=400)

    # Route through AI
    session = _get_or_create_channel_session(client, sender_psid, 'messenger')
    tenant = _get_tenant_for_client(client)
    if not _check_and_increment_message(tenant):
        return HttpResponse('OK')  # quota exceeded — silently skip
    try:
        result = generate_ai_response(session, text, {})
        reply_text = result.get('reply_text', 'Sorry, I could not process your request.')
    except Exception as e:
        logger.error(f'[messenger_webhook] AI error: {e}')
        reply_text = 'Sorry, something went wrong on my end.'

    _send_messenger_reply(client.messenger_page_access_token, sender_psid, reply_text)
    return HttpResponse('OK')


# ─── Telegram webhook ─────────────────────────────────────────────────────────

def _send_telegram_reply(bot_token, chat_id, text):
    try:
        http_requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={'chat_id': chat_id, 'text': text},
            timeout=10,
        )
    except Exception as e:
        logger.error(f'[telegram_reply] Failed: {e}')


def register_telegram_webhook(client):
    """Register our webhook URL with Telegram for this client's bot.

    Returns (ok: bool, message: str). Logs full detail on failure.
    Without this call, Telegram has no idea where to deliver messages —
    so toggling telegram_enabled=True in the UI alone does nothing.
    """
    from django.conf import settings as dj_settings
    if not client.telegram_bot_token:
        return False, 'No bot token configured'

    backend = (getattr(dj_settings, 'BACKEND_PUBLIC_URL', '') or 'https://ai.checkfunnels.com').rstrip('/')
    webhook_url = f'{backend}/api/chat/webhooks/telegram/{client.id}/'
    try:
        resp = http_requests.post(
            f'https://api.telegram.org/bot{client.telegram_bot_token}/setWebhook',
            json={'url': webhook_url, 'allowed_updates': ['message', 'edited_message']},
            timeout=10,
        )
        data = resp.json() if resp.content else {}
        if resp.ok and data.get('ok'):
            logger.info(f'[telegram] Webhook registered for client {client.id} → {webhook_url}')
            return True, 'Webhook registered'
        err = data.get('description') or f'HTTP {resp.status_code}'
        logger.error(f'[telegram] Webhook registration FAILED for client {client.id}: {err}')
        return False, err
    except Exception as e:
        logger.exception(f'[telegram] Webhook registration exception for client {client.id}: {e}')
        return False, str(e)


def delete_telegram_webhook(bot_token):
    """Tell Telegram to stop sending us updates for this bot token."""
    if not bot_token:
        return True, 'No bot token'
    try:
        resp = http_requests.post(
            f'https://api.telegram.org/bot{bot_token}/deleteWebhook',
            timeout=10,
        )
        return resp.ok, 'Webhook deleted' if resp.ok else f'HTTP {resp.status_code}'
    except Exception as e:
        logger.warning(f'[telegram] Webhook delete failed: {e}')
        return False, str(e)


@api_view(['POST'])
@permission_classes([AllowAny])
def telegram_webhook(request, client_id):
    """Telegram Bot webhook — set via setWebhook to this URL."""
    try:
        client = Client.objects.get(pk=client_id)
    except (Client.DoesNotExist, Exception):
        return HttpResponse('Not found', status=404)

    if not client.telegram_enabled or not client.telegram_bot_token:
        return HttpResponse('Channel not configured', status=400)

    data = request.data
    try:
        message = data.get('message') or data.get('edited_message', {})
        chat_id = str(message['chat']['id'])
        text = message.get('text')
        if not text:
            return HttpResponse('OK')  # sticker / photo — ignore
    except (KeyError, TypeError):
        return HttpResponse('OK')

    session = _get_or_create_channel_session(client, chat_id, 'telegram')
    tenant = _get_tenant_for_client(client)
    if not _check_and_increment_message(tenant):
        return HttpResponse('OK')  # quota exceeded — silently skip
    try:
        result = generate_ai_response(session, text, {})
        reply_text = result.get('reply_text', 'Sorry, I could not process your request.')
    except Exception as e:
        logger.error(f'[telegram_webhook] AI error: {e}')
        reply_text = 'Sorry, something went wrong on my end.'

    _send_telegram_reply(client.telegram_bot_token, chat_id, reply_text)
    return HttpResponse('OK')

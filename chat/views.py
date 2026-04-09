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


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ChatRateThrottle, SessionRateThrottle])
def chat_message(request):
    session_id = request.data.get('session_id')
    message = request.data.get('message')
    behavior_matrix = request.data.get('behavior_matrix', {})

    if not session_id or not message:
        return Response({'error': 'session_id and message are required'}, status=status.HTTP_400_BAD_REQUEST)

    session, _ = ChatSession.objects.get_or_create(session_id=session_id)
    ai_response = generate_ai_response(session, message, behavior_matrix)
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
            'chatbot_logo_url': None,
            'cta_message': "You're clearly ready — grab your exclusive discount:",
            'fomo_offer_text': None,
            'fomo_countdown_seconds': 600,
            'discount_code': None,
        })

    return Response({
        'chatbot_name': client.chatbot_name,
        'chatbot_color': client.chatbot_color,
        'chatbot_logo_url': client.chatbot_logo_url,
        'cta_message': client.cta_message,
        'fomo_offer_text': client.fomo_offer_text,
        'fomo_countdown_seconds': client.fomo_countdown_seconds,
        'discount_code': client.discount_code,
        'voice_input_enabled': client.voice_input_enabled,
        'image_input_enabled': client.image_input_enabled,
    })


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

    # Build FOMO message based on trigger type
    if trigger_type == 'exit_intent':
        fomo_msg = (
            client.fomo_offer_text
            or (
                f"Wait! Before you go — use code **{client.discount_code}** for an exclusive discount!"
                if client.discount_code
                else "Wait! Don't leave yet — I can help you find exactly what you're looking for."
            )
        )
    else:  # pricing_hesitation
        fomo_msg = (
            client.fomo_offer_text
            or (
                f"Still deciding? Use code **{client.discount_code}** — limited time only!"
                if client.discount_code
                else "Still deciding? I can walk you through our plans and find the best fit for you."
            )
        )

    # Add countdown hint if configured
    if client.fomo_countdown_seconds and client.fomo_countdown_seconds > 0:
        mins = client.fomo_countdown_seconds // 60
        fomo_msg += f" This offer expires in {mins} minutes!"

    # Persist to chat history
    history = session.chat_history or []
    history.append({'role': 'ai', 'message': fomo_msg, 'source': trigger_type})
    ChatSession.objects.filter(session_id=session_id).update(
        chat_history=history,
        closing_triggered=True,
    )

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
    Called by the widget lead-capture modal to save visitor email/phone to the session.
    Body: { session_id, email, phone? }
    """
    session_id = request.data.get('session_id')
    email = request.data.get('email', '').strip()

    if not session_id or not email:
        return Response({'error': 'session_id and email required'}, status=status.HTTP_400_BAD_REQUEST)

    phone = request.data.get('phone', '') or ''

    updated = ChatSession.objects.filter(session_id=session_id).update(
        lead_email=email,
        lead_phone=phone or None,
    )

    if not updated:
        return Response({'error': 'session not found'}, status=status.HTTP_404_NOT_FOUND)

    # Reload session for webhook payload
    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
        client = session.client
        if client:
            from chat.utils import fire_slack_notification, fire_outbound_webhook
            slack_text = (
                f':mega: *Lead Captured on {client.name}*\n'
                f'Email: {email}' + (f' · Phone: {phone}' if phone else '')
            )
            fire_slack_notification(client, slack_text)
            fire_outbound_webhook(client, 'lead_captured', {
                'session_id': str(session_id),
                'visitor_id': session.visitor_id,
                'lead_email': email,
                'lead_phone': phone or '',
            })
    except Exception:
        pass

    # Fire HubSpot sync asynchronously if client has integration configured
    try:
        from users.tasks import sync_lead_to_hubspot
        sync_lead_to_hubspot.delay(str(session_id))
    except Exception:
        pass

    return Response({'status': 'saved'})


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
        http_requests.post(
            'https://graph.facebook.com/v20.0/me/messages',
            params={'access_token': page_access_token},
            json={
                'recipient': {'id': recipient_id},
                'message': {'text': text},
            },
            timeout=10,
        )
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
    try:
        result = generate_ai_response(session, text, {})
        reply_text = result.get('reply_text', 'Sorry, I could not process your request.')
    except Exception as e:
        logger.error(f'[telegram_webhook] AI error: {e}')
        reply_text = 'Sorry, something went wrong on my end.'

    _send_telegram_reply(client.telegram_bot_token, chat_id, reply_text)
    return HttpResponse('OK')

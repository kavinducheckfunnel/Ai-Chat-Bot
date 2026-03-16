from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import ChatSession
from .ai_service import generate_ai_response
from users.models import Client
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@api_view(['POST'])
@permission_classes([AllowAny])
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

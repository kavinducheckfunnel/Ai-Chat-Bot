from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import ChatSession
from .ai_service import generate_ai_response
from users.permissions import IsTenantAdmin


# ─────────────────────────────────────────────────────────────────────────────
# Public chat endpoint (HTTP fallback — primary path is WebSocket)
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def chat_message(request):
    session_id = request.data.get('session_id')
    message = request.data.get('message')
    behavior_matrix = request.data.get('behavior_matrix', {})

    if not session_id or not message:
        return Response({'error': 'session_id and message are required'}, status=400)

    session, _ = ChatSession.objects.get_or_create(session_id=session_id)
    ai_response = generate_ai_response(session, message, behavior_matrix)
    return Response(ai_response)


# ─────────────────────────────────────────────────────────────────────────────
# Lead Kanban — sessions grouped by conversation_state
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsTenantAdmin])
def kanban_board(request):
    """
    Returns sessions grouped by conversation_state, sorted by heat_score desc.
    Tenant admins see only their clients' sessions; superadmins see all.
    """
    from users.models import TenantProfile

    role = request.user.profile.role
    qs = ChatSession.objects.select_related('client').order_by('-heat_score')

    if role == 'tenant_admin':
        try:
            client_ids = list(request.user.tenant_profile.clients.values_list('id', flat=True))
            qs = qs.filter(client_id__in=client_ids)
        except TenantProfile.DoesNotExist:
            qs = ChatSession.objects.none()

    states = ['RESEARCH', 'EVALUATION', 'OBJECTION', 'RECOVERY', 'READY_TO_BUY']
    board = {}
    for state in states:
        sessions = qs.filter(conversation_state=state)[:30]
        board[state] = [_session_card(s) for s in sessions]

    return Response(board)


@api_view(['PATCH'])
@permission_classes([IsTenantAdmin])
def session_update(request, session_id):
    """Admin manually moves a session to a different state."""
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)

    new_state = request.data.get('conversation_state')
    if new_state and new_state in dict(ChatSession.STATE_CHOICES):
        session.conversation_state = new_state
        session.save(update_fields=['conversation_state'])

    return Response(_session_card(session))


# ─────────────────────────────────────────────────────────────────────────────
# God View — human takeover
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsTenantAdmin])
def takeover_session(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)

    session.takeover_active = True
    session.taken_over_by = request.user
    session.save(update_fields=['takeover_active', 'taken_over_by'])
    return Response({'status': 'takeover active', 'session_id': str(session_id)})


@api_view(['POST'])
@permission_classes([IsTenantAdmin])
def release_session(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)

    session.takeover_active = False
    session.taken_over_by = None
    session.save(update_fields=['takeover_active', 'taken_over_by'])
    return Response({'status': 'released', 'session_id': str(session_id)})


@api_view(['POST'])
@permission_classes([IsTenantAdmin])
def admin_send_message(request, session_id):
    """Admin injects a message into the visitor chat (bypasses AI)."""
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)

    message = request.data.get('message', '').strip()
    if not message:
        return Response({'error': 'message required'}, status=400)

    session.chat_history.append({'role': 'ai', 'message': message})
    session.save(update_fields=['chat_history'])

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{session_id}",
        {
            'type': 'chat_message',
            'message': message,
            'sender': 'ai',
            'admin_injected': True,
        }
    )
    return Response({'status': 'sent'})


# ─────────────────────────────────────────────────────────────────────────────
# FOMO trigger endpoint — widget reports exit-intent or pricing page hesitation
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def fomo_trigger(request):
    """
    Called by useTracker.js when exit-intent or pricing hesitation is detected.
    Injects a FOMO message into the session's chat via WebSocket.
    """
    session_id = request.data.get('session_id')
    trigger_type = request.data.get('trigger_type', 'exit_intent')  # or 'pricing_hesitation'

    if not session_id:
        return Response({'error': 'session_id required'}, status=400)

    try:
        session = ChatSession.objects.select_related('client').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)

    client = session.client
    if not client:
        return Response({'status': 'no client configured'})

    if trigger_type == 'exit_intent':
        offer_text = client.fomo_offer_text or "Wait! Before you go — check out our special offer!"
    else:
        offer_text = client.fomo_offer_text or "Still comparing? Here's why this is the right choice for you."

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{session_id}",
        {
            'type': 'chat_message',
            'message': offer_text,
            'sender': 'ai',
            'is_fomo': True,
            'countdown_seconds': client.fomo_countdown_seconds,
        }
    )
    return Response({'status': 'fomo triggered', 'message': offer_text})


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _session_card(s):
    last_msg = ''
    if s.chat_history:
        last_msg = s.chat_history[-1].get('message', '')[:80]
    return {
        'session_id': str(s.session_id),
        'visitor_id': s.visitor_id,
        'heat_score': s.heat_score,
        'conversation_state': s.conversation_state,
        'message_count': s.message_count,
        'last_message': last_msg,
        'updated_at': s.updated_at.isoformat() if s.updated_at else None,
        'takeover_active': s.takeover_active,
        'client_id': str(s.client_id) if s.client_id else None,
        'client_name': s.client.name if s.client else None,
    }

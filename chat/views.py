from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatSession
from .ai_service import generate_ai_response

@api_view(['POST'])
def chat_message(request):
    session_id = request.data.get('session_id')
    message = request.data.get('message')
    behavior_matrix = request.data.get('behavior_matrix', {})
    
    if not session_id or not message:
        return Response({'error': 'session_id and message are required'}, status=status.HTTP_400_BAD_REQUEST)
        
    session, _ = ChatSession.objects.get_or_create(session_id=session_id)
    
    ai_response = generate_ai_response(session, message, behavior_matrix)
    
    return Response(ai_response)

from rest_framework import generics, serializers
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from django.db.models import Count, Avg
from users.models import Client
from chat.models import ChatSession
from django.shortcuts import get_object_or_404

class ClientSerializer(serializers.ModelSerializer):
    session_count = serializers.IntegerField(read_only=True, required=False)
    class Meta:
        model = Client
        fields = '__all__'

# --- Client Management ---

class ClientListCreateView(generics.ListCreateAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        # Annotate session_count only for list view
        return Client.objects.annotate(session_count=Count('sessions')).order_by('-created_at')

class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAdminUser]

# --- Stats & Analytics ---

@api_view(['GET'])
@permission_classes([IsAdminUser])
def global_stats(request):
    total_clients = Client.objects.count()
    total_sessions = ChatSession.objects.count()
    active_sessions = ChatSession.objects.filter(message_count__gt=0).count()
    
    # State aggregation for the funnel
    state_counts = ChatSession.objects.values('conversation_state').annotate(count=Count('conversation_id')).order_by('conversation_state')
    funnel = {item['conversation_state']: item['count'] for item in state_counts}
    
    return Response({
        "total_clients": total_clients,
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "revenue_estimate": total_clients * 49.0,
        "funnel": funnel,
        "daily_trend": [12, 19, 15, 22, 30, 25, 40] # Placeholder for bar chart
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def client_sessions(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    sessions = ChatSession.objects.filter(client=client).order_by('-updated_at')
    
    # Simple list return
    data = []
    for s in sessions:
        data.append({
            "session_id": str(s.session_id),
            "visitor_id": s.visitor_id,
            "message_count": s.message_count,
            "state": s.conversation_state,
            "updated_at": s.updated_at,
            "intent_score": s.current_intent_ema
        })
    
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def client_analytics(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    sessions = ChatSession.objects.filter(client=client)
    
    state_counts = sessions.values('conversation_state').annotate(count=Count('conversation_id'))
    funnel = {item['conversation_state']: item['count'] for item in state_counts}
    
    avg_intent = sessions.aggregate(Avg('current_intent_ema'))['current_intent_ema__avg'] or 0
    
    return Response({
        "funnel": funnel,
        "avg_intent": avg_intent,
        "sessions_trend": [5, 8, 3, 10, 12, 7, 15] # Placeholder
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def session_detail(request, session_id):
    session = get_object_or_404(ChatSession, session_id=session_id)
    return Response({
        "session_id": str(session.session_id),
        "chat_history": session.chat_history,
        "behavioral_context": session.behavioral_context,
        "state": session.conversation_state,
        "scores": {
            "intent": session.current_intent_ema,
            "budget": session.current_budget_ema,
            "urgency": session.current_urgency_ema
        }
    })

# --- Actions ---

@api_view(['GET'])
@permission_classes([AllowAny])
def get_public_config(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    return Response({
        "name": client.chatbot_name,
        "color": client.chatbot_color,
        "logo_url": client.chatbot_logo_url
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_scrape(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    
    # In a real app, this would be a Celery task
    from scraper.ingestion import process_and_store_website_data
    
    if not client.domain_url:
        return Response({"error": "Client has no domain URL"}, status=400)
    
    # Set status to running
    client.ingestion_status = 'RUNNING'
    client.save()
    
    try:
        # For Demo/MVP, we run it synchronously (Careful: blocks request)
        # In production, use delay() with Celery
        process_and_store_website_data(client.domain_url, client=client)
        
        client.ingestion_status = 'DONE'
        # Update page count
        from scraper.models import DocumentChunk
        client.total_pages_ingested = DocumentChunk.objects.filter(client=client).values('source_url').distinct().count()
        client.save()
        
        return Response({"status": "Success", "pages": client.total_pages_ingested})
    except Exception as e:
        client.ingestion_status = 'FAILED'
        client.save()
        return Response({"error": str(e)}, status=500)

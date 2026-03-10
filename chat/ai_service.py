import os
import json
from pgvector.django import CosineDistance
from scraper.models import DocumentChunk
from scraper.embeddings import get_embeddings_model
from .prompts import build_prompt, GEMINI_SCHEMA
from .ema_engine import update_session_scores
from .state_machine import update_session_state
from google import genai
from google.genai import types

def generate_ai_response(session, user_message, behavior_matrix):
    # 1. Generate embedding for user message
    embedder = get_embeddings_model()
    query_embedding = embedder.embed_query(user_message)
    
    # Pad to 1536 if needed
    if len(query_embedding) < 1536:
        query_embedding = query_embedding + [0.0] * (1536 - len(query_embedding))
    elif len(query_embedding) > 1536:
        query_embedding = query_embedding[:1536]
    
    # 2. Similarity Search using CosineDistance
    top_chunks = DocumentChunk.objects.annotate(
        distance=CosineDistance('embedding', query_embedding)
    ).order_by('distance')[:5]
    
    # 3. Construct Prompt
    system_prompt, user_prompt = build_prompt(
        session.conversation_state,
        top_chunks,
        behavior_matrix,
        session.chat_history,
        user_message
    )
    
    # 4. Call Gemini with Structured Output
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    response = client.models.generate_content(
        model='gemini-2.5-flash', # Or gemini-2.0-flash
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    
    # In some versions of google-genai, response_schema could be passed.
    # Otherwise, we ask for JSON explicitly in the prompt.
    # The new SDK takes "response_schema" mapped from a dict if possible,
    # but let's rely on JSON parsing since we requested application/json.
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        result = {
            "reply_text": "I encountered an error processing your request.",
            "intent_score": 0.5,
            "budget_score": 0.5,
            "urgency_score": 0.5
        }
    
    # 5. Update session scores
    update_session_scores(
        session,
        raw_intent=result.get('intent_score', 0.5),
        raw_budget=result.get('budget_score', 0.5),
        raw_urgency=result.get('urgency_score', 0.5)
    )
    
    # 6. Update conversation state
    update_session_state(session)
    
    # Update chat history
    session.chat_history.append({'role': 'user', 'message': user_message})
    session.chat_history.append({'role': 'ai', 'message': result.get('reply_text')})
    session.save(update_fields=['chat_history'])
    
    return result

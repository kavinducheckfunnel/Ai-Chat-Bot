import os
import json
from pgvector.django import CosineDistance
from scraper.models import DocumentChunk
from scraper.embeddings import get_embeddings_model
from .prompts import build_prompt, GEMINI_SCHEMA
from .ema_engine import update_session_scores
from .state_machine import update_session_state
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
import boto3

def generate_ai_response(session, user_message, behavior_matrix):
    # 1. Generate embedding for user message
    embedder = get_embeddings_model()
    query_embedding = embedder.embed_query(user_message)
    
    # Pad to 1536 if needed
    if len(query_embedding) < 1536:
        query_embedding = query_embedding + [0.0] * (1536 - len(query_embedding))
    elif len(query_embedding) > 1536:
        query_embedding = query_embedding[:1536]
    
    # 2. Similarity Search using CosineDistance filtered by Client
    chunk_qs = DocumentChunk.objects.filter(client=session.client) if session.client else DocumentChunk.objects.all()
    
    top_chunks = chunk_qs.annotate(
        distance=CosineDistance('embedding', query_embedding)
    ).order_by('distance')[:40]
    
    # 3. Construct Prompt (injecting the schema instructions explicitly for DeepSeek)
    client_domain = session.client.domain_url if session.client and hasattr(session.client, 'domain_url') else "Unknown"
    
    system_prompt, user_prompt = build_prompt(
        session.conversation_state,
        top_chunks,
        behavior_matrix,
        session.chat_history,
        user_message,
        website_domain=client_domain
    )
    
    # Force JSON output via instruction
    system_prompt += "\n\nCRITICAL: You MUST return ONLY a valid raw JSON object matching this schema. NO markdown formatting, NO conversational text outside the JSON block. schema:\n" + json.dumps(GEMINI_SCHEMA)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    
    # 4. Call Deepseek v3.2 with Structured Output using Friend's Keys from ENV (Fallback Mode for Demos)
    friend_client = boto3.client(
        service_name='bedrock-runtime',
        aws_access_key_id=os.environ.get("FRIEND_AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("FRIEND_AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
    )
    
    llm = ChatBedrockConverse(
        model="deepseek.v3.2",
        client=friend_client,
        temperature=0.7,
    )
    
    try:
        raw_result = llm.invoke(messages)
        content = raw_result.content
        
        # Strip markdown syntax if deepseek returns ```json ... ```
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        result = json.loads(content)
        
        if not result:
            raise ValueError("Empty response parsed from DeepSeek")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Bedrock Error / Parsing Error: {e}\nRaw Content: {raw_result.content if 'raw_result' in locals() else 'N/A'}")
        result = {
            "reply_text": "I encountered an error processing your request on Bedrock.",
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

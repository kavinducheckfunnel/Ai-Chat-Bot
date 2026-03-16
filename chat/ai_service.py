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
    if session is None:
        return {
            "reply_text": "I'm sorry, but I couldn't establish a valid chat session. Please refresh the page and try again.",
            "intent_score": 0.0,
            "budget_score": 0.0,
            "urgency_score": 0.0
        }

    # ── 1. Embed the user query ──────────────────────────────────────────────
    embedder = get_embeddings_model()
    query_embedding = embedder.embed_query(user_message)
    
    # Pad to 1024 if needed
    if len(query_embedding) < 1024:
        query_embedding = query_embedding + [0.0] * (1024 - len(query_embedding))
    elif len(query_embedding) > 1024:
        query_embedding = query_embedding[:1024]
    
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

    # Append JSON-schema instruction for DeepSeek structured output
    system_prompt += (
        "\n\nCRITICAL: You MUST return ONLY a valid raw JSON object matching this schema. "
        "NO markdown code fences, NO extra text outside the JSON.\nSchema:\n"
        + json.dumps(GEMINI_SCHEMA)
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # ── 4. Call DeepSeek via AWS Bedrock ─────────────────────────────────────
    friend_client = boto3.client(
        service_name='bedrock-runtime',
        aws_access_key_id=os.environ.get("FRIEND_AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("FRIEND_AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
    )

    llm = ChatBedrockConverse(
        model="us.deepseek.r1-v1:0",
        client=friend_client,
        temperature=0.7,
    )

    raw_result = None
    try:
        raw_result = llm.invoke(messages)
        content = raw_result.content

        # DeepSeek R1 via Bedrock returns a list of content blocks:
        # [{'type': 'text', 'text': '...'}, {'type': 'reasoning_content', ...}]
        # Extract only the 'text' block(s).
        if isinstance(content, list):
            text_parts = [
                part.get('text', '')
                for part in content
                if isinstance(part, dict) and part.get('type') == 'text'
            ]
            content = ''.join(text_parts).strip()

        # Strip markdown code fences if DeepSeek wraps its output
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Strip any leading <think>…</think> reasoning blocks (text-mode fallback)
        if "<think>" in content and "</think>" in content:
            content = content.split("</think>")[-1].strip()

        result = json.loads(content)

        if not result:
            raise ValueError("Empty JSON parsed from DeepSeek response")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raw_content = raw_result.content if raw_result else "N/A"
        print(f"[AI Service] Bedrock/Parsing error: {e}\nRaw content: {raw_content}")
        result = {
            "reply_text": (
                "I'm sorry, I ran into a technical issue. "
                "Please try again in a moment."
            ),
            "intent_score": 0.5,
            "budget_score": 0.5,
            "urgency_score": 0.5,
        }

    # ── 5. Update EMA scores & conversation state ────────────────────────────
    update_session_scores(
        session,
        raw_intent=result.get('intent_score', 0.5),
        raw_budget=result.get('budget_score', 0.5),
        raw_urgency=result.get('urgency_score', 0.5),
    )
    update_session_state(session)

    # ── 6. Persist chat history ──────────────────────────────────────────────
    session.chat_history.append({'role': 'user', 'message': user_message})
    session.chat_history.append({'role': 'ai', 'message': result.get('reply_text', '')})
    session.save(update_fields=['chat_history'])

    return result

import os
import json
import boto3
from pgvector.django import CosineDistance
from scraper.models import DocumentChunk
from scraper.embeddings import get_embeddings_model
from .prompts import build_prompt, GEMINI_SCHEMA
from .ema_engine import update_session_scores
from .state_machine import update_session_state


def generate_ai_response(session, user_message, behavior_matrix):
    if session is None:
        return {
            "reply_text": "I'm sorry, but I couldn't establish a valid chat session. Please refresh the page and try again.",
            "intent_score": 0.0,
            "budget_score": 0.0,
            "urgency_score": 0.0
        }

    try:
        # ── 1. Embed the user query ──────────────────────────────────────────
        embedder = get_embeddings_model()
        query_embedding = embedder.embed_query(user_message)

        # Ensure exactly 1024 dims
        if len(query_embedding) < 1024:
            query_embedding = query_embedding + [0.0] * (1024 - len(query_embedding))
        elif len(query_embedding) > 1024:
            query_embedding = query_embedding[:1024]

        # ── 2. Similarity search filtered by client ──────────────────────────
        chunk_qs = DocumentChunk.objects.filter(client=session.client) if session.client else DocumentChunk.objects.all()
        # Fetch all chunks sorted by distance, deferring the heavy embedding
        # vectors (only needed for the SQL computation, not in Python).
        # Limit 3000 is generous enough for any site while avoiding runaway queries.
        raw_chunks = list(
            chunk_qs.annotate(
                distance=CosineDistance('embedding', query_embedding)
            ).order_by('distance').defer('embedding')[:3000]
        )

        # Pick the BEST (closest) chunk per unique URL — this ensures ALL pages
        # can surface, not just those whose many duplicate chunks dominate the top-N.
        seen_urls: set = set()
        top_chunks = []
        for chunk in raw_chunks:
            url = chunk.source_url or ''
            if url not in seen_urls:
                top_chunks.append(chunk)
                seen_urls.add(url)
            if len(top_chunks) >= 25:
                break

        # ── 3. Build prompt ──────────────────────────────────────────────────
        client_domain = session.client.domain_url if session.client and hasattr(session.client, 'domain_url') else "Unknown"
        system_prompt, user_prompt = build_prompt(
            session.conversation_state,
            top_chunks,
            behavior_matrix,
            session.chat_history,
            user_message,
            website_domain=client_domain
        )

        system_prompt += (
            "\n\nCRITICAL: You MUST return ONLY a valid raw JSON object matching this schema. "
            "NO markdown code fences, NO extra text outside the JSON.\nSchema:\n"
            + json.dumps(GEMINI_SCHEMA)
        )

        # ── 4. Call DeepSeek V3 via AWS Bedrock Converse API ─────────────────
        bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
        )

        resp = bedrock_client.converse(
            modelId="deepseek.v3.2",
            messages=[
                {"role": "user", "content": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
            ],
            inferenceConfig={"maxTokens": 2000, "temperature": 0.7, "topP": 0.9},
        )

        content_blocks = resp['output']['message']['content']
        raw_text = next((b['text'] for b in content_blocks if 'text' in b), '')

        # Strip markdown code fences if model wraps output
        content = raw_text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)

        if not result:
            raise ValueError("Empty JSON from LLM response")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[AI Service] Error: {e}")
        result = {
            "reply_text": "I'm sorry, I ran into a technical issue. Please try again in a moment.",
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

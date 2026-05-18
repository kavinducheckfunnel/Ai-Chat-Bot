import os
import json
import time
import logging
from pgvector.django import CosineDistance
from scraper.models import DocumentChunk
from scraper.embeddings import get_embeddings_model
from .prompts import build_prompt, GEMINI_SCHEMA
from .ema_engine import update_session_scores
from .state_machine import update_session_state
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

# Fallback chain used when the primary model is rate-limited.
# Index 0 is overridden by PlatformConfig.primary_model at runtime.
_PLATFORM_FALLBACK_MODELS = [
    'google/gemini-2.0-flash-001',
    'google/gemini-flash-1.5-8b',
    'meta-llama/llama-3.3-70b-instruct:free',
]


def _get_platform_config():
    """Return (api_key, primary_model) from DB, cached 60 s to avoid a DB hit per message."""
    from django.core.cache import cache
    cached = cache.get('platform_config')
    if cached:
        return cached
    try:
        from users.models import PlatformConfig
        cfg = PlatformConfig.get()
        key   = cfg.openrouter_api_key or os.environ.get('OPENROUTER_API_KEY', '')
        model = cfg.primary_model or _PLATFORM_FALLBACK_MODELS[0]
    except Exception:
        key   = os.environ.get('OPENROUTER_API_KEY', '')
        model = _PLATFORM_FALLBACK_MODELS[0]
    result = (key, model)
    cache.set('platform_config', result, 60)
    return result


def _make_openrouter_llm(model: str, api_key: str = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key or os.environ.get('OPENROUTER_API_KEY'),
        openai_api_base='https://openrouter.ai/api/v1',
        temperature=0.4,
        max_retries=1,
    )


def _build_llm(client):
    """
    Return a (llm, is_byok) tuple.
    Uses the client's BYOK key when configured, otherwise the platform default.
    """
    if client and client.ai_api_key and client.ai_model:
        provider = client.ai_provider or 'openrouter'
        if provider == 'openai':
            api_base = 'https://api.openai.com/v1'
        else:
            api_base = 'https://openrouter.ai/api/v1'
        return ChatOpenAI(
            model=client.ai_model,
            openai_api_key=client.ai_api_key,
            openai_api_base=api_base,
            temperature=0.4,
            max_retries=2,
        ), True
    api_key, primary_model = _get_platform_config()
    return _make_openrouter_llm(primary_model, api_key), False


def _invoke_with_fallback(messages, client):
    """
    Invoke the LLM. For platform (non-BYOK) requests, walk the fallback chain
    on 429 rate-limit errors so users never see an error message.
    """
    from openai import RateLimitError

    llm, is_byok = _build_llm(client)

    if is_byok:
        # BYOK — use their key directly, no fallback
        return llm.invoke(messages)

    # Platform — try primary model then static fallbacks
    api_key, primary_model = _get_platform_config()
    fallback_chain = [primary_model] + [m for m in _PLATFORM_FALLBACK_MODELS if m != primary_model]
    last_exc = None
    for i, model in enumerate(fallback_chain):
        llm = _make_openrouter_llm(model, api_key)
        try:
            result = llm.invoke(messages)
            if i > 0:
                logger.info(f'[ai] Rate-limited on primary, succeeded with fallback: {model}')
            return result
        except RateLimitError as e:
            logger.warning(f'[ai] 429 on {model}, trying next fallback. err={e}')
            last_exc = e
            time.sleep(0.5 * (i + 1))
        except Exception as e:
            raise e  # non-rate-limit errors bubble up immediately

    raise last_exc  # all fallbacks exhausted


def generate_ai_response(session, user_message, behavior_matrix, image_data=None):
    """
    Generate an AI response for a chat session.

    Args:
        session: ChatSession instance
        user_message: The user's text message
        behavior_matrix: Dict with behavioral signals from the widget tracker
        image_data: Optional base64-encoded image string (data URI or raw base64)
    """
    # 1. Generate embedding for user message
    embedder = get_embeddings_model()
    query_embedding = embedder.embed_query(user_message or 'image')

    # Pad / truncate to 1024 dims
    if len(query_embedding) < 1024:
        query_embedding = query_embedding + [0.0] * (1024 - len(query_embedding))
    elif len(query_embedding) > 1024:
        query_embedding = query_embedding[:1024]

    # 2. Similarity search filtered by client
    chunk_qs = (
        DocumentChunk.objects.filter(client=session.client)
        if session.client else DocumentChunk.objects.all()
    )
    top_chunks = chunk_qs.annotate(
        distance=CosineDistance('embedding', query_embedding)
    ).order_by('distance')[:40]

    # 3. Build prompt
    client_domain = (
        session.client.domain_url
        if session.client and hasattr(session.client, 'domain_url')
        else 'Unknown'
    )
    system_prompt, user_prompt = build_prompt(
        session.conversation_state,
        top_chunks,
        behavior_matrix,
        session.chat_history,
        user_message,
        website_domain=client_domain,
    )
    system_prompt += (
        '\n\nCRITICAL: You MUST return ONLY a valid raw JSON object matching this schema. '
        'NO markdown formatting, NO conversational text outside the JSON block. schema:\n'
        + json.dumps(GEMINI_SCHEMA)
    )

    # 4. Build message list — multimodal if image attached
    if image_data:
        # Strip data URI prefix (e.g. "data:image/jpeg;base64,")
        raw_b64 = image_data.split(',', 1)[1] if ',' in image_data else image_data
        human_content = [
            {'type': 'text', 'text': user_prompt},
            {
                'type': 'image_url',
                'image_url': {'url': f'data:image/jpeg;base64,{raw_b64}'},
            },
        ]
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_content),
        ]
    else:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

    # 5. Call LLM (BYOK or platform default with fallback chain)
    try:
        raw_result = _invoke_with_fallback(messages, session.client)
        content = raw_result.content

        # Strip markdown code fences if model wraps output
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)
        if not result:
            raise ValueError('Empty response parsed from LLM')

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(
            f'[ai] LLM Error: {e} | '
            f"Raw: {raw_result.content if 'raw_result' in locals() else 'N/A'}"
        )
        result = {
            'reply_text': "Sorry, I'm having a little trouble right now. Please try again in a moment!",
            'intent_score': 0.5,
            'budget_score': 0.5,
            'urgency_score': 0.5,
        }

    # 6. Update EMA scores
    update_session_scores(
        session,
        raw_intent=result.get('intent_score', 0.5),
        raw_budget=result.get('budget_score', 0.5),
        raw_urgency=result.get('urgency_score', 0.5),
    )

    # 7. Update conversation state machine
    update_session_state(session)

    # 8. Persist chat history
    session.chat_history.append({'role': 'user', 'message': user_message or '[image]'})
    session.chat_history.append({'role': 'ai', 'message': result.get('reply_text')})

    from .utils import truncate_chat_history
    update_fields = truncate_chat_history(session)
    session.save(update_fields=update_fields)

    return result

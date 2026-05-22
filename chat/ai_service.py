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
from .qualification import (
    detect_qualification,
    render_for_prompt as render_qualification,
    URGENCY_KEYWORDS,
    BUY_PHRASES,
)
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


def build_browsing_context(session):
    """
    Build human-readable browsing context for the AI prompt from session data.

    Returns a dict that gets injected into behavior_matrix so the LLM can naturally
    reference what the visitor was looking at before opening the chat. Without this,
    the prompt only sees raw URLs and numeric signals — opaque to natural conversation.

    Output shape:
      {
        'pages':         [{title, url, dwell_seconds, is_product}, ...],
        'top_interest':  'Premium Blue Hoodie' | None,
        'signals':       ['Added to cart 2×', 'Viewed pricing 3×', ...],
        'heat_level':    'HIGH' | 'MEDIUM' | 'LOW',
        'is_returning':  bool,
        'is_first_msg':  bool,    # true when chat_history is empty
      }
    """
    if not session:
        return {}

    visits = session.page_visits or []

    # Match visited URLs against scraped DocumentChunks for clean titles
    url_to_title = {}
    if session.client and visits:
        visit_urls = [v.get('url') for v in visits if v.get('url')]
        if visit_urls:
            # Use absolute URLs where possible
            qs = DocumentChunk.objects.filter(
                client=session.client,
                source_url__in=visit_urls,
            ).only('source_url', 'metadata')
            for c in qs:
                meta = c.metadata or {}
                title = meta.get('title')
                if title and c.source_url:
                    url_to_title[c.source_url] = title

    def _is_product(url):
        return any(p in (url or '') for p in [
            '/product/', '/products/', '/shop/', '/item/', '/p/',
        ])

    pages = []
    for v in visits[-8:]:  # last 8 pages, most relevant
        url = v.get('url') or ''
        clean_title = url_to_title.get(url) or v.get('title') or url
        pages.append({
            'title': clean_title,
            'url': url,
            'dwell_seconds': v.get('duration_seconds', 0),
            'is_product': _is_product(url),
        })

    # Top interest = most-recently-viewed product page (any dwell ≥ 1s).
    # Earlier we required ≥ 10s, but real visitors browse quickly (2-4s per
    # page is common on ecommerce). Strict threshold killed personalization
    # for fast browsers. Now: prefer longest dwell, but fall back to most
    # recent product if no product has long dwell.
    products = [p for p in pages if p['is_product'] and p['dwell_seconds'] >= 1]
    if products:
        # Sort by dwell desc; ties broken by recency (later in list = more recent)
        products_sorted = sorted(
            enumerate(products),
            key=lambda kv: (kv[1]['dwell_seconds'], kv[0]),
            reverse=True,
        )
        top_interest = products_sorted[0][1]
    else:
        top_interest = None

    # Human-readable signals from behavioral_context
    ctx = session.behavioral_context or {}
    signals = []
    if ctx.get('add_to_cart_clicks'):
        signals.append(f"Added to cart {ctx['add_to_cart_clicks']}×")
    if ctx.get('checkout_visits'):
        signals.append(f"Visited checkout {ctx['checkout_visits']}×")
    if ctx.get('pricing_page_visits', 0) >= 1:
        signals.append(f"Viewed pricing {ctx['pricing_page_visits']}×")
    if ctx.get('price_views', 0) >= 3:
        signals.append(f"Viewed price elements {ctx['price_views']}×")
    if ctx.get('copy_events'):
        signals.append(f"Copied content {ctx['copy_events']}× (likely pricing/SKUs)")
    if ctx.get('form_focused') and not ctx.get('form_abandoned'):
        signals.append("Started filling a form")
    if ctx.get('form_abandoned'):
        signals.append("Abandoned a form")
    if ctx.get('cta_clicks', 0) >= 2:
        signals.append(f"Clicked CTAs {ctx['cta_clicks']}×")
    if ctx.get('scroll_depth', 0) >= 75:
        signals.append(f"Scrolled deeply ({ctx['scroll_depth']}%)")
    if ctx.get('video_plays'):
        signals.append(f"Played video {ctx['video_plays']}×")
    if ctx.get('file_downloads'):
        signals.append(f"Downloaded files {ctx['file_downloads']}×")
    if ctx.get('rage_clicks'):
        signals.append("Showed frustration (rage clicks)")

    # Heat level from composite EMA
    heat = (
        session.current_intent_ema * 0.45 +
        session.current_budget_ema * 0.30 +
        session.current_urgency_ema * 0.25
    ) * 100
    heat_level = 'HIGH' if heat > 60 else 'MEDIUM' if heat > 30 else 'LOW'

    # First message detection — based on the user's own messages only, not
    # bot greetings or auto-fired triggers (exit_intent / abandoned_form etc.
    # that fired BEFORE the visitor said anything). Without this, the AI
    # would think it's mid-conversation even when the visitor's first words
    # have just arrived.
    user_msgs = [m for m in (session.chat_history or []) if m.get('role') == 'user']
    is_first_msg = len(user_msgs) == 0

    return {
        'pages': pages,
        'top_interest': top_interest['title'] if top_interest else None,
        'top_interest_dwell': top_interest['dwell_seconds'] if top_interest else 0,
        'top_interest_url': top_interest['url'] if top_interest else None,
        'signals': signals,
        'heat_level': heat_level,
        'is_returning': bool(getattr(session, 'visitor_is_returning', False)),
        'is_first_msg': is_first_msg,
    }

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


# Cost estimation table — USD per 1M tokens (prompt, completion).
# Source: published OpenRouter / Anthropic / OpenAI pricing as of 2026-Q2.
# Conservative defaults for unknown models so cost is never wildly off.
# Single source of truth referenced by _log_llm_call() below.
_MODEL_PRICING_PER_1M = {
    'openai/gpt-4o':                  (2.50, 10.00),
    'openai/gpt-4o-mini':             (0.15,  0.60),
    'openai/gpt-4.1':                 (2.00,  8.00),
    'openai/gpt-4.1-mini':            (0.40,  1.60),
    'anthropic/claude-3-5-sonnet':    (3.00, 15.00),
    'anthropic/claude-3-5-haiku':     (1.00,  5.00),
    'anthropic/claude-3-haiku':       (0.25,  1.25),
    'google/gemini-2.0-flash-001':    (0.10,  0.40),
    'google/gemini-pro-1.5':          (1.25,  5.00),
    'meta-llama/llama-3.3-70b-instruct': (0.59, 0.79),
}
_DEFAULT_PRICE = (1.00, 3.00)  # fallback for unknown models


def _estimate_cost(model, prompt_tokens, completion_tokens):
    """Compute USD cost from a model id + token counts. Lookup is exact-match
    on the model string (no normalisation) since the table uses canonical
    OpenRouter ids."""
    if not (prompt_tokens or completion_tokens):
        return 0
    p_rate, c_rate = _MODEL_PRICING_PER_1M.get(model, _DEFAULT_PRICE)
    cost = (prompt_tokens or 0) * p_rate / 1_000_000 + (completion_tokens or 0) * c_rate / 1_000_000
    return round(cost, 6)


def _log_llm_call(*, client, model, provider, is_byok, latency_ms,
                  result=None, status='ok', fallback_from='', error_message='',
                  system_prompt_hash=''):
    """
    Write an LLMCallLog row. Best-effort — any exception here is swallowed
    so logging issues never bubble up and break a chat reply.
    """
    try:
        from chat.models import LLMCallLog

        prompt_t = completion_t = total_t = None
        if result is not None:
            try:
                meta = getattr(result, 'response_metadata', {}) or {}
                usage = meta.get('token_usage') or meta.get('usage') or {}
                prompt_t     = usage.get('prompt_tokens') or usage.get('input_tokens')
                completion_t = usage.get('completion_tokens') or usage.get('output_tokens')
                total_t      = usage.get('total_tokens')
                if total_t is None and (prompt_t or completion_t):
                    total_t = (prompt_t or 0) + (completion_t or 0)
            except Exception:
                pass

        cost = _estimate_cost(model, prompt_t or 0, completion_t or 0) if not is_byok else 0

        LLMCallLog.objects.create(
            client=client,
            model=model[:120],
            provider=provider,
            is_byok=is_byok,
            latency_ms=int(latency_ms),
            prompt_tokens=prompt_t,
            completion_tokens=completion_t,
            total_tokens=total_t,
            cost_usd=cost,
            status=status,
            fallback_from=fallback_from[:120],
            error_message=(error_message or '')[:5000],
            prompt_hash=system_prompt_hash[:16],
        )
    except Exception as e:
        logger.warning(f'[ai] LLMCallLog write failed: {e}')


def _hash_messages(messages):
    """Short stable hash of the system prompt for prompt A/B grouping."""
    try:
        import hashlib
        sys = next((m.content for m in messages if isinstance(m, SystemMessage)), '')
        return hashlib.md5(sys.encode('utf-8', 'replace')).hexdigest()[:16]
    except Exception:
        return ''


def _invoke_with_fallback(messages, client):
    """
    Invoke the LLM. For platform (non-BYOK) requests, walk the fallback chain
    on 429 rate-limit errors so users never see an error message.

    Every llm.invoke() — successful or failed — writes an LLMCallLog row
    so the MLOps dashboards can break down cost, latency, fallback rate,
    and BYOK vs platform spend without sampling.
    """
    from openai import RateLimitError

    llm, is_byok = _build_llm(client)
    prompt_hash = _hash_messages(messages)

    if is_byok:
        # BYOK — use their key directly, no fallback
        model = getattr(llm, 'model_name', None) or getattr(client, 'ai_model', '') or ''
        provider = (getattr(client, 'ai_provider', None) or 'openrouter') if client else 'openrouter'
        start = time.time()
        try:
            result = llm.invoke(messages)
            _log_llm_call(
                client=client, model=model, provider=provider, is_byok=True,
                latency_ms=(time.time() - start) * 1000,
                result=result, status='ok',
                system_prompt_hash=prompt_hash,
            )
            return result
        except Exception as e:
            _log_llm_call(
                client=client, model=model, provider=provider, is_byok=True,
                latency_ms=(time.time() - start) * 1000,
                status='error', error_message=str(e),
                system_prompt_hash=prompt_hash,
            )
            raise

    # Platform — try primary model then static fallbacks
    api_key, primary_model = _get_platform_config()
    fallback_chain = [primary_model] + [m for m in _PLATFORM_FALLBACK_MODELS if m != primary_model]
    last_exc = None
    for i, model in enumerate(fallback_chain):
        llm = _make_openrouter_llm(model, api_key)
        start = time.time()
        try:
            result = llm.invoke(messages)
            latency = (time.time() - start) * 1000
            if i > 0:
                logger.info(f'[ai] Rate-limited on primary, succeeded with fallback: {model}')
            _log_llm_call(
                client=client, model=model, provider='openrouter', is_byok=False,
                latency_ms=latency, result=result,
                status='fallback_used' if i > 0 else 'ok',
                fallback_from=fallback_chain[0] if i > 0 else '',
                system_prompt_hash=prompt_hash,
            )
            return result
        except RateLimitError as e:
            latency = (time.time() - start) * 1000
            logger.warning(f'[ai] 429 on {model}, trying next fallback. err={e}')
            _log_llm_call(
                client=client, model=model, provider='openrouter', is_byok=False,
                latency_ms=latency,
                status='rate_limited', error_message=str(e),
                system_prompt_hash=prompt_hash,
            )
            last_exc = e
            time.sleep(0.5 * (i + 1))
        except Exception as e:
            _log_llm_call(
                client=client, model=model, provider='openrouter', is_byok=False,
                latency_ms=(time.time() - start) * 1000,
                status='error', error_message=str(e),
                system_prompt_hash=prompt_hash,
            )
            raise e  # non-rate-limit errors bubble up immediately

    raise last_exc  # all fallbacks exhausted


# ─────────────────────────────────────────────────────────────────────────────
# Sales-enablement helpers — keyword-based score floors and kanban promotion
# ─────────────────────────────────────────────────────────────────────────────

def _urgency_score_floor(user_message: str) -> float:
    """
    Belt-and-suspenders for urgency: even if the LLM under-scores a clear
    urgency signal ("need it today!"), we floor urgency_score to 0.85 when
    any urgency keyword appears. Returns 0.0 if no signal.

    The keywords list lives in qualification.URGENCY_KEYWORDS so the same
    detector powers both the qualification checklist and the score floor —
    one source of truth.
    """
    if not user_message:
        return 0.0
    msg = user_message.lower()
    for kw in URGENCY_KEYWORDS:
        if kw in msg:
            return 0.85
    return 0.0


def _intent_score_floor(user_message: str) -> float:
    """
    Same idea for buying intent: a phrase like "I'll take it" or "I'm
    interested in buying" should floor intent at 0.9 regardless of what
    the LLM returned.
    """
    if not user_message:
        return 0.0
    msg = user_message.lower()
    for kw in BUY_PHRASES:
        if kw in msg:
            return 0.9
    return 0.0


def _budget_score_floor(user_message: str) -> float:
    """
    Implicit budget tolerance — when the visitor says "I'll take it" or
    "I want to buy this", they've effectively accepted the displayed price.
    Without this floor, budget_ema stays around 0.5-0.7 even after explicit
    purchase intent, and the state machine never reaches READY_TO_BUY
    because that requires budget > 0.8 too. Floor at 0.75 — high enough
    to push state forward, low enough that an explicit budget-objection
    later still works.
    """
    if not user_message:
        return 0.0
    msg = user_message.lower()
    for kw in BUY_PHRASES:
        if kw in msg:
            return 0.75
    return 0.0


def _recompute_heat_score(session) -> float:
    """
    Mirror of consumers.refresh_and_persist_heat()'s heat formula so the
    score gets calculated whether the AI is invoked over WebSocket or
    via direct HTTP / Celery / management commands. Keeps qualification
    detection (which checks heat >= 75) reliable across all entry points.

    Formula: weighted average of the 3 EMAs scaled to 0–100.
    """
    intent  = session.current_intent_ema  or 0
    budget  = session.current_budget_ema  or 0
    urgency = session.current_urgency_ema or 0
    score = (intent * 0.45 + budget * 0.30 + urgency * 0.25) * 100
    return round(min(score, 100), 1)


def _maybe_promote_kanban(session) -> bool:
    """
    Auto-promote the kanban_state to HOT_LEAD or QUALIFIED when the
    EMA/heat thresholds warrant it. Returns True if a change was made
    so the caller can broadcast it.

    Rules (most-aggressive wins):
      • heat_score >= 75 OR (intent>=0.8 AND urgency>=0.7) → HOT_LEAD
      • intent >= 0.6 AND state in NEW/CONTACTED → QUALIFIED
    Never demotes — a tenant can manually revert via Kanban DnD.
    """
    current = (session.kanban_state or '').upper()
    intent  = session.current_intent_ema or 0
    urgency = session.current_urgency_ema or 0
    heat    = session.heat_score or 0

    HOT_STATES_REACHABLE = {'NEW', 'CONTACTED', 'QUALIFIED'}

    if (heat >= 75 or (intent >= 0.8 and urgency >= 0.7)) and current in HOT_STATES_REACHABLE:
        session.kanban_state = 'HOT_LEAD'
        return True
    if intent >= 0.6 and current == 'NEW':
        session.kanban_state = 'QUALIFIED'
        return True
    return False


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

    # 2. Similarity search — STRICTLY scoped to the session's client.
    # Never fall back to .all() — that would leak content across tenants.
    # F10 — top-K dropped from 40 to 8. Average chunk is ~200 tokens, so 40
    # chunks = ~8000 tokens of KB context per request. Production showed
    # avg prompt at 9500 tokens with KB dominating. 8 chunks is industry
    # standard for RAG and the LLM rarely needs more than 3-5 to answer.
    # The 5x extra chunks were padding cost without improving quality.
    KB_TOP_K = 8
    if session.client_id:
        chunk_qs = DocumentChunk.objects.filter(client_id=session.client_id)
        top_chunks = chunk_qs.annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).order_by('distance')[:KB_TOP_K]
    else:
        # No client → no knowledge base. AI will rely solely on the system
        # persona + conversation history. Log so we can detect mis-routing.
        logger.warning(f'[ai] session {session.session_id} has no client_id — returning empty chunks')
        top_chunks = DocumentChunk.objects.none()

    # 3. Build prompt — enrich behavior_matrix with human-readable browsing context
    #    so the AI can naturally reference what the visitor was looking at.
    client_domain = (
        session.client.domain_url
        if session.client and hasattr(session.client, 'domain_url')
        else 'Unknown'
    )
    try:
        enriched_behavior = dict(behavior_matrix or {})
        enriched_behavior['browsing_summary'] = build_browsing_context(session)
    except Exception as e:
        logger.warning(f'[ai] build_browsing_context failed: {e}')
        enriched_behavior = behavior_matrix or {}

    # 3b. Build the qualification checklist — what's been answered vs missing.
    # This is the single most important sales-enablement upgrade: without it
    # the LLM has no idea what to ASK NEXT and slips back into Q/A mode.
    try:
        qualification_block = render_qualification(detect_qualification(session))
    except Exception as e:
        logger.warning(f'[ai] qualification detect failed: {e}')
        qualification_block = ''

    # Pull tenant-configured pre-purchase FAQ blurbs so the bot can answer
    # "return policy?" and "shipping?" inline instead of deflecting (C3, C5).
    faq_blurbs = {
        'return_policy': (getattr(session.client, 'return_policy_blurb', '') or '').strip() if session.client else '',
        'shipping': (getattr(session.client, 'shipping_blurb', '') or '').strip() if session.client else '',
    }

    system_prompt, user_prompt = build_prompt(
        session.conversation_state,
        top_chunks,
        enriched_behavior,
        session.chat_history,
        user_message,
        website_domain=client_domain,
        qualification_block=qualification_block,
        faq_blurbs=faq_blurbs,
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
    # Floor the LLM-reported scores with keyword-based detectors so a clear
    # "need it today!" can't be scored 0.4 by an under-confident model.
    # The flooring is a MAX() against the LLM number — never decreases it.
    raw_intent  = max(float(result.get('intent_score', 0.5)),  _intent_score_floor(user_message))
    raw_budget  = max(float(result.get('budget_score', 0.5)),  _budget_score_floor(user_message))
    raw_urgency = max(float(result.get('urgency_score', 0.5)), _urgency_score_floor(user_message))

    update_session_scores(
        session,
        raw_intent=raw_intent,
        raw_budget=raw_budget,
        raw_urgency=raw_urgency,
    )

    # 7. Update conversation state machine
    update_session_state(session)

    # 7b. Recompute heat_score in the AI service path too — previously it
    # was only computed by the WS consumer's refresh_and_persist_heat(),
    # which meant non-WS callers (Celery tasks, tests, management commands)
    # never saw heat update. The qualification module's is_hot_lead check
    # depends on heat>=75 as one of its triggers.
    session.heat_score = _recompute_heat_score(session)

    # 7c. Auto-promote kanban_state to HOT_LEAD / QUALIFIED when scores warrant
    # it. Saves the field if changed so the dashboard reflects reality
    # without a tenant having to drag the card manually.
    kanban_changed = _maybe_promote_kanban(session)

    # Single combined save covers both heat and (optional) kanban update.
    update_fields = ['heat_score']
    if kanban_changed:
        update_fields.append('kanban_state')
    session.save(update_fields=update_fields)

    # 8. Persist chat history
    session.chat_history.append({'role': 'user', 'message': user_message or '[image]'})
    session.chat_history.append({'role': 'ai', 'message': result.get('reply_text')})

    from .utils import truncate_chat_history
    update_fields = truncate_chat_history(session)
    session.save(update_fields=update_fields)

    return result

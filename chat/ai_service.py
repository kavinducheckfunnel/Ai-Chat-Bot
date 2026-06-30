import os
import re
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

def detect_current_focus(session, top_chunks, user_message):
    """
    Determine the product/category the visitor is CURRENTLY interested in,
    derived from their most-recent chat messages — the opposite of the
    dwell-weighted browsing `top_interest`, which is sticky to whatever
    they looked at longest and never updates when they pivot in chat.

    Why this exists: a visitor who browsed caps (long dwell) then asks the
    bot about hoodies kept getting asked about caps, because `top_interest`
    stayed "Cap" and dominated the prompt every turn. This function reads
    the latest user message(s), matches them against the client's known
    product/category titles (from the retrieved KB chunks), and returns the
    freshest match. The caller treats this as authoritative over browsing
    `top_interest` once the visitor has typed about a product.

    Returns the matched title string, or '' when nothing matches.

    Cheap by design — pure string matching against chunk titles, no extra
    embedding or LLM call.
    """
    try:
        # Weight the current message heaviest, then the previous user turn.
        history = getattr(session, 'chat_history', None) or []
        prior_user = [m.get('message', '') for m in history if m.get('role') == 'user']
        # Most-recent-first: current message, then last typed message.
        candidates_text = []
        if user_message:
            candidates_text.append(user_message.lower())
        if prior_user:
            candidates_text.append((prior_user[-1] or '').lower())
        if not candidates_text:
            return ''

        # Build the title vocabulary from retrieved chunks (these are the
        # products/categories most relevant to THIS query already).
        titles = []
        for ch in top_chunks:
            meta = ch.metadata if isinstance(getattr(ch, 'metadata', None), dict) else {}
            t = (meta.get('title') or '').strip()
            if t and t.lower() not in {x.lower() for x in titles}:
                titles.append(t)

        # Match: a title whose significant words appear in the recent text.
        # Check the current message first so a fresh pivot wins immediately.
        for text in candidates_text:
            best = ''
            best_len = 0
            for title in titles:
                tl = title.lower()
                # Full-title substring match is the strongest signal.
                if tl in text and len(tl) > best_len:
                    best, best_len = title, len(tl)
                    continue
                # Otherwise match on the title's longest word (e.g. "hoodie"
                # in "Hoodie with Zipper") so generic category words still hit.
                # `s?` tolerates plurals ("hoodie" ↔ "hoodies") — the most
                # common reason a focus pivot was missed. The trailing word
                # boundary still blocks false hits like "cap" → "capable".
                words = [w for w in re.findall(r'[a-z]{4,}', tl)]
                for w in words:
                    if re.search(r'\b' + re.escape(w) + r's?\b', text) and len(w) > best_len:
                        best, best_len = title, len(w)
            if best:
                return best
        return ''
    except Exception as e:
        logger.warning(f'[detect_current_focus] {e}')
        return ''


# Fallback chain used when the primary model is rate-limited.
# Index 0 is overridden by PlatformConfig.primary_model at runtime.
_PLATFORM_FALLBACK_MODELS = [
    'google/gemini-2.0-flash-001',
    'google/gemini-flash-1.5-8b',
    'meta-llama/llama-3.3-70b-instruct:free',
]

# Separate chain used when the request carries an image. The text-only
# llama is removed; if the geminis rate-limit we route to a small
# vision-capable model instead so image messages never silently fail.
_PLATFORM_VISION_FALLBACK_MODELS = [
    'google/gemini-2.0-flash-001',
    'google/gemini-flash-1.5-8b',
    'openai/gpt-4o-mini',
]

# Image data URIs land here as `data:image/<subtype>;base64,<payload>`.
# `_parse_image_data_uri` returns (mime, base64_payload). MIME is sniffed
# instead of hard-coded so PNG / WebP / GIF aren't mislabeled as JPEG —
# Anthropic via OpenRouter rejects mismatched MIME and even Gemini behaves
# better with the real type.
_ALLOWED_IMAGE_MIME = ('image/png', 'image/jpeg', 'image/gif', 'image/webp')


def _parse_image_data_uri(image_data: str) -> tuple[str, str]:
    """
    Split a data URI into (mime, base64_payload).

    Falls back to ('image/jpeg', <whole string>) when the input is a raw
    base64 blob without a `data:` prefix — backwards-compatible with old
    widget builds. Unknown MIMEs are normalised to image/jpeg so we never
    pass an unsupported type downstream.
    """
    if not image_data:
        return 'image/jpeg', ''
    if not image_data.startswith('data:'):
        return 'image/jpeg', image_data
    try:
        header, payload = image_data.split(',', 1)
    except ValueError:
        return 'image/jpeg', image_data
    # header looks like `data:image/png;base64`
    mime = 'image/jpeg'
    if ';' in header:
        mime_part = header.split(';', 1)[0].replace('data:', '', 1).strip().lower()
        if mime_part in _ALLOWED_IMAGE_MIME:
            mime = mime_part
    return mime, payload


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


def _invoke_with_fallback(messages, client, vision_required: bool = False):
    """
    Invoke the LLM. For platform (non-BYOK) requests, walk the fallback chain
    on 429 rate-limit errors so users never see an error message.

    When `vision_required=True` the platform path uses
    `_PLATFORM_VISION_FALLBACK_MODELS` instead — the standard chain ends
    with a text-only llama which 400s on multimodal content blocks.

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
            # For image messages, a BYOK model that is text-only (or otherwise
            # rejects multimodal content blocks) would dead-end the visitor
            # with a generic error. Instead of raising, fall through to the
            # platform vision chain below so the image still gets answered.
            if vision_required:
                logger.warning(
                    f'[ai] BYOK model {model!r} failed on a vision request '
                    f'({e}); falling back to platform vision models.'
                )
            else:
                raise

    # Platform — try primary model then static fallbacks
    api_key, primary_model = _get_platform_config()
    base_chain = (
        _PLATFORM_VISION_FALLBACK_MODELS if vision_required else _PLATFORM_FALLBACK_MODELS
    )
    fallback_chain = [primary_model] + [m for m in base_chain if m != primary_model]
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


def compute_kanban_stage(session) -> str:
    """Return the kanban stage a session SHOULD be in, derived purely from its
    metrics (the same heat/intent matrix the dashboard shows). Used by the
    `recompute_kanban_states` backfill to move every lead to its correct column.

    Terminal / explicitly-advanced stages are preserved (never auto-reverted):
      CONVERTED, LOST, READY_TO_BUY.
    Otherwise, most-advanced wins:
      heat>=75 or (intent>=0.8 & urgency>=0.7) → HOT_LEAD
      intent>=0.6                              → QUALIFIED
      has >=1 visitor message                  → ENGAGED
      else                                     → NEW
    """
    cur = (session.kanban_state or '').upper()
    if cur in ('CONVERTED', 'LOST', 'READY_TO_BUY'):
        return cur
    intent = session.current_intent_ema or 0
    urgency = session.current_urgency_ema or 0
    budget = session.current_budget_ema or 0
    heat = (intent * 0.45 + budget * 0.30 + urgency * 0.25) * 100
    email = (getattr(session, 'lead_email', '') or '').strip()
    phone = (getattr(session, 'lead_phone', '') or '').strip()
    if (session.conversation_state or '').upper() == 'READY_TO_BUY':
        return 'READY_TO_BUY'
    if heat >= 75 or (intent >= 0.8 and urgency >= 0.7):
        return 'HOT_LEAD'
    # A captured contact (email or phone) is a strong buying signal — keep these
    # as hot leads even if the EMA scores have since cooled, so real leads don't
    # sink back into the pile.
    if email or phone:
        return 'HOT_LEAD'
    if intent >= 0.6:
        return 'QUALIFIED'
    if (session.message_count or 0) >= 1:
        return 'ENGAGED'
    return 'NEW'


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

    # ENGAGED is included so an active chatter can still climb to QUALIFIED/HOT;
    # otherwise the new NEW→ENGAGED auto-move below would trap it in ENGAGED.
    HOT_STATES_REACHABLE = {'NEW', 'ENGAGED', 'CONTACTED', 'QUALIFIED'}

    if (heat >= 75 or (intent >= 0.8 and urgency >= 0.7)) and current in HOT_STATES_REACHABLE:
        session.kanban_state = 'HOT_LEAD'
        return True
    if intent >= 0.6 and current in ('', 'NEW', 'ENGAGED'):
        session.kanban_state = 'QUALIFIED'
        return True
    # The visitor has engaged (this runs in the AI-reply path) but hasn't hit the
    # qualify/hot thresholds yet → move out of NEW into ENGAGED automatically so
    # active chatters don't pile up in the New column. Only NEW (or unset) sessions
    # are touched; never demotes a further stage.
    if current in ('', 'NEW') and (session.message_count or 0) >= 1:
        session.kanban_state = 'ENGAGED'
        return True
    return False


def _promote_lead_on_capture(session):
    """Promote the kanban stage after an inline contact capture (QA #13).

    Mirrors the explicit lead-modal logic, minus the injected confirmation
    message (the AI already replied conversationally):
      • BOTH email + phone     → CONVERTED (the conversion event for this funnel)
      • a SINGLE valid contact → HOT_LEAD (a captured email OR phone is a real,
                                 qualified lead on its own — no heat gate)
    Never demotes. Saves the session if it changed.
    """
    cur = (session.kanban_state or '').upper()
    has_email = bool((session.lead_email or '').strip())
    has_phone = bool((session.lead_phone or '').strip())
    if not (has_email or has_phone):
        return
    new_state = None
    if has_email and has_phone and cur not in {'CONVERTED', 'LOST'}:
        new_state = 'CONVERTED'
    elif cur in {'NEW', 'ENGAGED', 'CONTACTED', 'QUALIFIED'}:
        new_state = 'HOT_LEAD'
    if new_state and new_state != cur:
        session.kanban_state = new_state
        try:
            session.save(update_fields=['kanban_state'])
        except Exception:
            pass


import re as _re

# "List everything you sell" type queries. Normal RAG retrieval only returns
# the top-K nearest chunks (5-10), so the bot would list ~5 products and look
# like the catalogue is tiny. When one of these matches we inject the FULL
# product list into context so the bot can list them all.
_CATALOG_PATTERNS = _re.compile(
    r'\b('
    r'list (all|your|the|every|out)|show (all|me all|me your|me every|everything)|'
    r'all (your |the )?(products|items|stock)|'
    r'(full|entire|complete|whole) (product |item )?(list|catalog|catalogue|range|collection|inventory)|'
    r'what (products|items|do you (sell|have|offer|stock|carry))|'
    r'everything you (sell|have|offer|stock|carry)|'
    r'(product|item|catalog|catalogue) list|'
    r'what (kinds?|types?|range) of (products|items)|'
    r'(give|show) me (a |the )?(product |full )?(list|catalog|catalogue)'
    r')\b',
    _re.IGNORECASE,
)


def _is_catalog_query(msg):
    return bool(msg) and bool(_CATALOG_PATTERNS.search(msg))


class _CatalogChunk:
    """Lightweight stand-in for a DocumentChunk so build_prompt can render the
    injected catalogue with the same [Source Title]/[Source URL]/content shape.
    """
    def __init__(self, content, title='Full product catalog', url=''):
        self.content = content
        self.source_url = url
        self.metadata = {'title': title, 'type': 'catalog'}


def _build_catalog_chunk(client_id, website_domain=''):
    """Compose a compact 'all products' block (name — price — url), de-duped by
    product name so duplicated Shopify handles don't list the same item twice.
    Returns a _CatalogChunk or None when there are no products.
    """
    qs = DocumentChunk.objects.filter(client_id=client_id, metadata__type='product')
    try:
        qs = qs.exclude(metadata__is_active=False)
    except Exception:
        pass
    rows, seen = [], set()
    for ch in qs.only('content', 'source_url', 'metadata'):
        md = ch.metadata if isinstance(ch.metadata, dict) else {}
        title = (md.get('title') or '').strip()
        key = title.lower()
        if not title or key in seen:
            continue
        seen.add(key)
        price = (md.get('price_display') or '').strip()
        url = ch.source_url or ''
        line = f'- {title}'
        if price:
            line += f' — {price}'
        if url:
            line += f' — {url}'
        rows.append(line)
        if len(rows) >= 100:
            break
    if not rows:
        return None
    header = (
        f'COMPLETE PRODUCT CATALOGUE — these are ALL {len(rows)} products currently '
        f'available on the store. When the visitor asks to list or show all products, '
        f'list EVERY item below (you may number them and group sensibly, but do NOT '
        f'omit items or imply the catalogue is only a handful). Keep each product\'s '
        f'name as a markdown link to its URL.\n\n'
    )
    return _CatalogChunk(header + '\n'.join(rows), 'Full product catalogue', website_domain)


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
    #
    # F10 + bonus: dynamic top-K by conversation state. Higher-intent
    # states need richer context (exact specs, variants, stock); browsing
    # states just need orientation. Saves ~25% additional tokens on
    # average without hurting close-quality.
    #
    # Baseline: 8 (post-F10 from 40)
    # RESEARCH:    5  → visitor still browsing, doesn't need deep specs yet
    # EVALUATION:  8  → comparing options, default coverage
    # OBJECTION:   8  → defending the recommendation, default
    # RECOVERY:    6  → re-engagement, brief context
    # READY_TO_BUY:10 → exact match matters; variant + stock detail useful
    KB_TOP_K_BY_STATE = {
        'RESEARCH': 5,
        'EVALUATION': 8,
        'OBJECTION': 8,
        'RECOVERY': 6,
        'READY_TO_BUY': 10,
    }
    KB_TOP_K = KB_TOP_K_BY_STATE.get(session.conversation_state, 8)
    if session.client_id:
        chunk_qs = DocumentChunk.objects.filter(client_id=session.client_id)
        # Suppress chunks that were flagged sold-out by the Shopify
        # inventory webhook (Phase C). `is_active=False` on metadata
        # means every variant is out of stock — recommending it would be
        # a worse experience than skipping it. Chunks without the flag
        # (everything from WordPress, WC, custom crawl) stay visible.
        try:
            chunk_qs = chunk_qs.exclude(metadata__is_active=False)
        except Exception:
            # Some DB backends (SQLite in tests) don't support JSONField
            # `__is_active=False` lookups; the suppression is a soft
            # filter so falling back silently is fine.
            pass
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
    # Plus Q8 scarcity blurb for late-stage urgency injection.
    faq_blurbs = {
        'return_policy': (getattr(session.client, 'return_policy_blurb', '') or '').strip() if session.client else '',
        'shipping': (getattr(session.client, 'shipping_blurb', '') or '').strip() if session.client else '',
        'scarcity': (getattr(session.client, 'scarcity_blurb', '') or '').strip() if session.client else '',
    }

    # 3c. Current conversation focus — the product/category the visitor is
    # asking about RIGHT NOW (recency-weighted from chat), which overrides
    # the dwell-sticky browsing top_interest so a pivot ("now show hoodies")
    # is honoured instead of the bot looping on the first-browsed product.
    current_focus = detect_current_focus(session, top_chunks, user_message)

    # Catalogue-listing intent ("list all products"): normal top-K retrieval
    # only surfaces a handful of chunks, so prepend a full product list so the
    # bot can enumerate the whole catalogue instead of just the nearest few.
    prompt_chunks = list(top_chunks)
    if user_message and not image_data and session.client_id and _is_catalog_query(user_message):
        try:
            cat = _build_catalog_chunk(session.client_id, client_domain)
            if cat:
                prompt_chunks = [cat] + prompt_chunks
        except Exception as e:
            logger.warning(f'[ai] catalog injection failed: {e}')

    system_prompt, user_prompt, static_system, dynamic_system = build_prompt(
        session.conversation_state,
        prompt_chunks,
        enriched_behavior,
        session.chat_history,
        user_message,
        website_domain=client_domain,
        qualification_block=qualification_block,
        faq_blurbs=faq_blurbs,
        conversation_summary=session.conversation_summary or '',
        current_focus=current_focus,
    )

    # ── Order-status intent (Shopify-connected stores) ───────────────────────
    # If the visitor is asking about an order, look it up live and inject a
    # verified ORDER STATUS block so the bot answers from real data (never
    # invents a status). Verification = order number + matching email.
    order_block = ''
    if user_message and not image_data and session.client_id:
        try:
            from . import shopify_orders as _so
            if _so.is_order_query(user_message):
                client = session.client
                if _so.is_connected(client):
                    order_no = _so.extract_order_number(user_message)
                    email = (session.lead_email or '').strip()
                    if not email:
                        from .phone_utils import extract_email
                        email = extract_email(user_message) or ''
                    if order_no and email:
                        res = _so.lookup_order(client, order_no, email)
                        if res.get('ok'):
                            order_block = (
                                "\n\nORDER STATUS MODE — the visitor asked about an order and the "
                                "order number + email MATCHED. Answer naturally and warmly using "
                                "ONLY these verified facts (include the tracking link if present). "
                                "Never invent details.\n" + _so.format_order_context(res['order'])
                            )
                        elif res.get('reason') == 'not_found':
                            order_block = (
                                "\n\nORDER STATUS MODE — no order matched that number + email. "
                                "Politely say you couldn't find a match, ask them to double-check "
                                "both the order number and the email used on the order, and offer to "
                                "connect them with the team. NEVER reveal whether any order exists."
                            )
                        else:
                            order_block = (
                                "\n\nORDER STATUS MODE — order lookup is temporarily unavailable. "
                                "Apologize briefly and offer to have the team follow up."
                            )
                    else:
                        order_block = (
                            "\n\nORDER STATUS MODE — the visitor wants their order status. To look it "
                            "up you still need their ORDER NUMBER and the EMAIL used on the order. Ask "
                            "for both in ONE friendly sentence. Do not make up a status."
                        )
                else:
                    order_block = (
                        "\n\nORDER STATUS MODE — live order tracking isn't connected for this store. "
                        "Apologize briefly, then offer to pass their question to the team — ask for "
                        "their order number and email so a human can follow up."
                    )
        except Exception as e:
            logger.warning(f'[ai] order-status injection failed: {e}')
    if order_block:
        system_prompt += order_block
        dynamic_system += order_block  # Anthropic path reads dynamic_system, not system_prompt

    # ── Per-page behavior prompt (page_rules) ────────────────────────────────
    # If the tenant wrote a "how to act on this page" instruction for the page
    # the visitor is currently on, inject it so the AI tailors its replies
    # (e.g. on a product page focus on specs/sizing; on cart reassure on
    # shipping/returns). Derived from the visitor's most recent page visit.
    try:
        visits = session.page_visits or []
        if visits and session.client_id:
            from . import page_rules as _pr
            last = visits[-1] or {}
            last_url = last.get('url') or ''
            rule = _pr.match_rule(_pr.get_rules(session.client), last_url)
            bp = (rule or {}).get('behavior_prompt', '').strip() if rule else ''
            if bp:
                # Resolve any dynamic {tags} in the behaviour prompt with the
                # context we have server-side (page title ≈ product/category
                # name, client name = store name). Degrades gracefully.
                tag_values = {
                    'store_name': (session.client.name or session.client.chatbot_name or '').strip(),
                    'product_name': (last.get('title') or '').strip(),
                    'category_name': (last.get('title') or '').strip(),
                }
                # keep_unknown=True: fill {store_name}/{product_name}/… but leave
                # any other {placeholder} prose in the tenant's instruction intact.
                bp = _pr.resolve_greeting_text({'greeting_message': bp}, values=tag_values, keep_unknown=True)
                page_block = (
                    f"\n\nPAGE CONTEXT — the visitor is currently on the "
                    f"\"{rule.get('label', 'page')}\" page. {bp}"
                )
                system_prompt += page_block
                dynamic_system += page_block
    except Exception as e:
        logger.warning(f'[ai] page behavior injection failed: {e}')

    # ── Active offers / sales (tenant-declared promotions) ───────────────────
    # Inject currently-live offers as knowledge so the bot can mention them when
    # relevant and share the offer link. Date-gated → auto-expires. Separate
    # from the reactive FOMO/discount_code path (which is untouched).
    try:
        if session.client_id:
            from . import offers as _offers
            offs = _offers.active_offers(session.client)
            if offs:
                offer_block = _offers.format_offers_block(offs)
                system_prompt += offer_block
                dynamic_system += offer_block
    except Exception as e:
        logger.warning(f'[ai] offers injection failed: {e}')

    # JSON-mode tail-prompt — used for text-only turns. Vision turns get a
    # plain-text instruction instead: image-capable models reliably break
    # strict-JSON output when an image is also in the request, so forcing
    # JSON made every image upload fall into the "Sorry, I'm having a
    # little trouble" fallback. For image turns we ask for a normal
    # conversational reply and synthesise the scores ourselves from the
    # keyword floors.
    if image_data:
        system_prompt += (
            "\n\nThe visitor has attached an IMAGE along with their message. "
            "Look at the image, identify what's in it (product / packaging / "
            "screenshot / receipt / question), and answer the visitor's "
            "question directly in 1-3 plain conversational sentences. "
            "Do NOT return JSON, do NOT use markdown code blocks, do NOT "
            "wrap the reply in quotes — just write the reply text the "
            "visitor should see."
        )
        # Tighten the dynamic half too — Anthropic prompt-cache only sees
        # the static portion, so changes here don't bust the cache.
        dynamic_system += (
            "\n\nIMAGE INPUT MODE: respond with plain text only (no JSON, no markdown fences)."
        )
    else:
        system_prompt += (
            '\n\nCRITICAL: You MUST return ONLY a valid raw JSON object matching this schema. '
            'NO markdown formatting, NO conversational text outside the JSON block. schema:\n'
            + json.dumps(GEMINI_SCHEMA)
        )

    # 4. Build message list — multimodal if image attached
    # Anthropic prompt caching: wrap the static system portion in a
    # cache_control: ephemeral block so Anthropic charges full price once
    # per 5-min window, then ~10% per read. Static = persona + state +
    # FAQ blurbs (~3500 tokens). Dynamic = qualification + KB + history.
    # Only applied for Anthropic-routed models (direct or via OpenRouter)
    # — other providers ignore the cache_control hint (no-op).
    model_name = (
        (session.client.ai_model if session.client and session.client.ai_model else '')
        or _get_platform_config()[1]
        or ''
    ).lower()
    use_anthropic_cache = 'anthropic' in model_name or 'claude' in model_name

    if use_anthropic_cache:
        # Structured content blocks. cache_control marks the cache boundary
        # — Anthropic caches everything up to (and including) the marked
        # block, indexed by exact content hash.
        system_content = [
            {'type': 'text', 'text': static_system, 'cache_control': {'type': 'ephemeral'}},
            {'type': 'text', 'text': dynamic_system},
        ]
    else:
        system_content = system_prompt

    if image_data:
        mime, raw_b64 = _parse_image_data_uri(image_data)
        human_content = [
            {'type': 'text', 'text': user_prompt},
            {
                'type': 'image_url',
                'image_url': {'url': f'data:{mime};base64,{raw_b64}'},
            },
        ]
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content),
        ]
    else:
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_prompt),
        ]

    # 5. Call LLM (BYOK or platform default with fallback chain).
    # Image turns route through the vision-only chain so a rate-limited
    # primary doesn't fall through to a text-only fallback.
    try:
        raw_result = _invoke_with_fallback(
            messages, session.client, vision_required=bool(image_data),
        )
        content = raw_result.content

        if image_data:
            # Plain-text mode for image turns. Strip optional fences/quotes
            # and let the visitor see whatever the vision model wrote.
            text = (content or '').strip()
            if text.startswith('```'):
                # Tolerate accidental markdown fences even though we asked
                # for none — strip the first fenced block.
                parts = text.split('```')
                # parts looks like ['', 'maybe-lang\n actual text', '']
                if len(parts) >= 2:
                    inner = parts[1]
                    if '\n' in inner:
                        inner = inner.split('\n', 1)[1]
                    text = inner.strip()
            text = text.strip('"').strip("'").strip()
            # Vision models often IGNORE the "plain text, no JSON" instruction
            # and return the normal scoring object anyway. If so, pull the
            # fields out — otherwise the visitor sees a raw JSON blob.
            parsed_obj = None
            if text.startswith('{') and 'reply_text' in text:
                try:
                    import json as _json
                    cand = _json.loads(text)
                    if isinstance(cand, dict) and cand.get('reply_text'):
                        parsed_obj = cand
                except Exception:
                    parsed_obj = None

            def _score(v, d=0.5):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return d

            if parsed_obj:
                result = {
                    'reply_text': str(parsed_obj.get('reply_text') or '').strip(),
                    'intent_score': _score(parsed_obj.get('intent_score')),
                    'budget_score': _score(parsed_obj.get('budget_score')),
                    'urgency_score': _score(parsed_obj.get('urgency_score')),
                    'suggested_product_id': parsed_obj.get('suggested_product_id'),
                    'quick_replies': parsed_obj.get('quick_replies') or [],
                }
                if not result['reply_text']:
                    raise ValueError('Empty image reply from LLM')
            else:
                if not text:
                    raise ValueError('Empty image reply from LLM')
                # Synthesise the rest of the schema. Intent/budget/urgency come
                # from the keyword floors below (max() against these defaults
                # in step 6) so a purchase phrase in the visitor's message
                # still moves the EMAs even though the LLM didn't score.
                result = {
                    'reply_text': text,
                    'intent_score': 0.5,
                    'budget_score': 0.5,
                    'urgency_score': 0.5,
                    'suggested_product_id': None,
                    'quick_replies': [],
                }
        else:
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

    # 8. Persist chat history. For image turns store a `[image]` marker so
    # the summariser, qualification scanner, and follow-up turns can see
    # the visitor sent a picture. We deliberately don't archive the base64
    # payload — it's huge and the LLM only needs to know one was sent.
    if image_data and user_message:
        user_entry_text = f'[image attached] {user_message}'
    elif image_data:
        user_entry_text = '[image attached]'
    else:
        user_entry_text = user_message
    session.chat_history.append({'role': 'user', 'message': user_entry_text})
    session.chat_history.append({'role': 'ai', 'message': result.get('reply_text')})

    # 8b. Inline contact capture (QA #13) — detect an email and/or phone number
    # the visitor typed in this message and store them silently on the session
    # (only fields we don't already have). Replaces the old interrupting popup:
    # "call me on 077 123 4567" or "email me at jo@x.com" now lands in the CRM
    # in clean form, with no friction in the chat flow.
    if user_message:
        try:
            from .phone_utils import extract_phone, extract_email
            captured_fields = []
            country = getattr(session.client, 'lead_country', None) or 'LK'
            if not (session.lead_phone or '').strip():
                inline_phone = extract_phone(user_message, country)
                if inline_phone:
                    session.lead_phone = inline_phone
                    captured_fields.append('lead_phone')
            if not (session.lead_email or '').strip():
                inline_email = extract_email(user_message)
                if inline_email:
                    session.lead_email = inline_email
                    captured_fields.append('lead_email')
            if captured_fields:
                session.save(update_fields=captured_fields)
                _promote_lead_on_capture(session)
        except Exception as e:
            logger.warning(f'[ai] inline contact capture failed: {e}')

    from .utils import truncate_chat_history
    update_fields = truncate_chat_history(session)
    session.save(update_fields=update_fields)

    # Kick the rolling-summary task if the unsummarised tail is large
    # enough. Runs out-of-band in Celery — never blocks the reply.
    try:
        from .tasks import maybe_schedule_summary
        maybe_schedule_summary(session)
    except Exception as e:
        logger.warning(f'[ai] maybe_schedule_summary failed: {e}')

    return result

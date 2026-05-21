"""Runtime resolver for editable prompts.

`chat.prompts.build_prompt()` calls `get_system_persona()` and
`get_state_instructions()` from here instead of using the module-level
constants directly. This indirection lets the super admin edit prompts
from the UI without a redeploy.

Design:
  • Per-process LRU cache keyed by slug, ~60s TTL. Hot path = chat reply.
  • On any failure (DB down, parse error, missing row), fall back to the
    file constant. The chatbot never goes down because of this feature.
  • Cache is invalidated by `bump_cache(slug)` after a write — and also
    via Redis pub/sub so all daphne workers refresh in ~real time.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 60-second TTL is the SLA the editor UI advertises ("live within 60s").
CACHE_TTL_SECONDS = 60

# In-process cache: slug -> (expires_at_epoch, parsed_value)
_cache: Dict[str, tuple[float, Any]] = {}


def _file_default(slug: str) -> Any:
    """Return the factory-default value from chat.prompts."""
    # Local import avoids a circular import at module load time.
    from . import prompts as prompts_module
    if slug == 'system_persona':
        return prompts_module.SYSTEM_PERSONA
    if slug == 'state_instructions':
        return prompts_module.STATE_INSTRUCTIONS
    raise KeyError(f'Unknown prompt slug: {slug}')


def _parse(slug: str, body: str) -> Any:
    """Coerce the stored body to the type build_prompt() expects.

    `system_persona` is a plain string. `state_instructions` is a JSON-encoded
    dict (so super admin edits one editor box, not five).
    """
    if slug == 'system_persona':
        return body
    if slug == 'state_instructions':
        return json.loads(body)
    raise KeyError(f'Unknown prompt slug: {slug}')


def _load_from_db(slug: str) -> Optional[Any]:
    """Fetch the active version from DB, parse it, return parsed value.

    Returns None if no active version exists or the DB lookup fails — the
    caller will then fall back to the file constant. Any exception is
    caught and logged; the chatbot never breaks because of a prompt fetch.
    """
    try:
        # Local import keeps Django app loading order happy.
        from .models import PromptTemplate
        template = (
            PromptTemplate.objects
            .select_related('active_version')
            .filter(slug=slug)
            .first()
        )
        if template is None or template.active_version is None:
            return None
        return _parse(slug, template.active_version.body)
    except Exception:
        logger.exception('[prompt_service] DB load failed for slug=%s; using file default', slug)
        return None


def _get(slug: str) -> Any:
    """Resolve a prompt slug to its current value, with caching + fallback."""
    now = time.time()
    cached = _cache.get(slug)
    if cached and cached[0] > now:
        return cached[1]

    value = _load_from_db(slug)
    if value is None:
        # File default — also cache, so we don't hammer the DB during outage.
        value = _file_default(slug)

    _cache[slug] = (now + CACHE_TTL_SECONDS, value)
    return value


def get_system_persona() -> str:
    return _get('system_persona')


def get_state_instructions() -> dict:
    val = _get('state_instructions')
    # Defensive: if a malformed JSON ever slips past validation, fall back.
    if not isinstance(val, dict):
        logger.warning('[prompt_service] state_instructions is not a dict; using file default')
        return _file_default('state_instructions')
    return val


def bump_cache(slug: Optional[str] = None) -> None:
    """Invalidate the in-process cache.

    Called from the save/rollback view immediately, and from the Redis
    subscriber when another worker writes. `slug=None` clears everything
    (used by tests + manual debugging).
    """
    if slug is None:
        _cache.clear()
        return
    _cache.pop(slug, None)


# ─── Redis pub/sub for cross-worker invalidation ────────────────────────────
# Each daphne / celery worker keeps its own in-process cache. After a save
# we publish on `prompt:invalidate` so every worker drops its cache. The
# subscriber runs as a daemon thread started lazily on first save.

_INVALIDATE_CHANNEL = 'prompt:invalidate'
_subscriber_started = False


def publish_invalidate(slug: str) -> None:
    """Publish a cache-invalidate message for `slug` to all workers."""
    try:
        from django.core.cache import cache
        client = cache.client.get_client(write=True)  # django-redis raw client
        client.publish(_INVALIDATE_CHANNEL, slug)
    except Exception:
        # If Redis isn't available, in-process cache will still clear locally
        # and other workers will pick up the change after CACHE_TTL_SECONDS.
        logger.warning('[prompt_service] publish_invalidate failed for slug=%s', slug, exc_info=True)


def _start_subscriber_once() -> None:
    """Lazily start a daemon thread that listens for invalidate messages."""
    global _subscriber_started
    if _subscriber_started:
        return
    _subscriber_started = True

    def _run():
        try:
            from django.core.cache import cache
            client = cache.client.get_client(write=False)
            pubsub = client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(_INVALIDATE_CHANNEL)
            for msg in pubsub.listen():
                if msg.get('type') != 'message':
                    continue
                slug = msg.get('data')
                if isinstance(slug, bytes):
                    slug = slug.decode('utf-8')
                bump_cache(slug)
                logger.info('[prompt_service] cache invalidated via pubsub: slug=%s', slug)
        except Exception:
            logger.exception('[prompt_service] subscriber loop exited')

    import threading
    threading.Thread(target=_run, name='prompt-invalidate-subscriber', daemon=True).start()


def ensure_subscriber():
    """Public hook so views can ensure the subscriber is running."""
    _start_subscriber_once()

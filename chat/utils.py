import logging
import requests as _requests

logger = logging.getLogger(__name__)

_MAX_ACTIVE = 200
_ARCHIVE_BATCH = 50


def client_allows_image(client):
    """Whether image upload is available for this client's chat widget.

    Auto-enabled per plan: any tenant whose plan includes image input
    (Growth and up — Plan.allow_image_input) gets it without flipping the
    per-client `image_input_enabled` toggle. The explicit toggle still works
    as an override so a plan that doesn't include it can be granted ad-hoc.

    Used by the widget config endpoint (to show/hide the upload button), the
    REST + WebSocket ingest guards (to strip stray image payloads), so all
    three agree. Safe to call with None.
    """
    if not client:
        return False
    if getattr(client, 'image_input_enabled', False):
        return True
    try:
        tp = client.tenantprofile_set.select_related('plan').first()
        return bool(tp and tp.plan and tp.plan.allow_image_input)
    except Exception:
        return False


def fire_slack_notification(client, text):
    """POST a plain-text message to the client's Slack incoming webhook (if configured)."""
    if not client or not client.slack_webhook_url:
        return
    try:
        _requests.post(
            client.slack_webhook_url,
            json={'text': text},
            timeout=5,
        )
    except Exception as e:
        logger.warning(f'[fire_slack_notification] client={client.id}: {e}')


def fire_outbound_webhook(client, event, payload):
    """
    POST a JSON event to the client's outbound webhook URL (if configured and event enabled).
    payload: dict of event-specific data.
    """
    if not client or not client.outbound_webhook_url:
        return
    enabled_events = [e.strip() for e in (client.outbound_webhook_events or '').split(',')]
    if event not in enabled_events:
        return
    import time
    body = {
        'event': event,
        'timestamp': int(time.time()),
        'client_id': str(client.id),
        'client_name': client.name,
        **payload,
    }
    try:
        _requests.post(
            client.outbound_webhook_url,
            json=body,
            timeout=8,
            headers={'Content-Type': 'application/json', 'X-Checkfunnel-Event': event},
        )
    except Exception as e:
        logger.warning(f'[fire_outbound_webhook] client={client.id} event={event}: {e}')


def truncate_chat_history(session, max_active=_MAX_ACTIVE, archive_batch=_ARCHIVE_BATCH):
    """
    If session.chat_history exceeds max_active entries, move the oldest
    archive_batch items into chat_history_archive.

    Also shifts `summary_through_index` left by the same amount so the
    rolling-summary pointer keeps referring to the same logical position
    in the post-trim history. Without this, the summariser would re-scan
    already-summarised messages on every subsequent run (or worse, skip
    new ones because the index pointed past the new end).

    Returns the list of update_fields that need to be saved.

    Also stamps `last_message_at` — this helper is only ever called right
    after appending message(s) to chat_history, so it's the canonical place
    to record true last-message recency for the inbox (see ChatSession.
    last_message_at). Callers must persist the returned fields.
    """
    from django.utils import timezone
    session.last_message_at = timezone.now()

    if len(session.chat_history) > max_active:
        overflow = session.chat_history[:archive_batch]
        session.chat_history_archive = (session.chat_history_archive or []) + overflow
        session.chat_history = session.chat_history[archive_batch:]
        fields = ['chat_history', 'chat_history_archive', 'last_message_at']
        if hasattr(session, 'summary_through_index'):
            session.summary_through_index = max(
                0, (session.summary_through_index or 0) - archive_batch,
            )
            fields.append('summary_through_index')
        return fields
    return ['chat_history', 'last_message_at']

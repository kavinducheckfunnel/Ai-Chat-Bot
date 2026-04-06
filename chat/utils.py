import logging
import requests as _requests

logger = logging.getLogger(__name__)

_MAX_ACTIVE = 200
_ARCHIVE_BATCH = 50


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

    Returns the list of update_fields that need to be saved.
    """
    if len(session.chat_history) > max_active:
        overflow = session.chat_history[:archive_batch]
        session.chat_history_archive = (session.chat_history_archive or []) + overflow
        session.chat_history = session.chat_history[archive_batch:]
        return ['chat_history', 'chat_history_archive']
    return ['chat_history']

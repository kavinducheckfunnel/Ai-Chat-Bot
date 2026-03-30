_MAX_ACTIVE = 200
_ARCHIVE_BATCH = 50


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

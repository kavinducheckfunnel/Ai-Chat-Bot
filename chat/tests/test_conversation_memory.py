"""
Tests for the conversation-memory feature (Phases 1-3).

Covers:
  • _is_high_signal — slot-bearing message detector
  • _select_recent_history — verbatim window + slot-promoted older msgs
  • build_prompt — summary block injection + correct history slice
  • truncate_chat_history — summary_through_index pointer shifts with archive
  • maybe_schedule_summary — threshold check
  • summarize_chat_session — incremental update path with mocked LLM
  • end-to-end via generate_ai_response with a mocked LLM
"""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from chat.models import ChatSession
from chat.prompts import (
    build_prompt,
    _is_high_signal,
    _select_recent_history,
    CHAT_HISTORY_WINDOW,
    CHAT_HISTORY_HARD_CAP,
)
from chat.utils import truncate_chat_history


# ─── _is_high_signal ─────────────────────────────────────────────────────────

class TestIsHighSignal:
    def test_email_is_high_signal(self):
        assert _is_high_signal({'role': 'user', 'message': 'reach me at jane@example.com'})

    def test_phone_is_high_signal(self):
        assert _is_high_signal({'role': 'user', 'message': 'call me on +94 71 234 5678'})

    def test_currency_is_high_signal(self):
        assert _is_high_signal({'role': 'user', 'message': 'my budget is around $250'})

    def test_textual_currency_is_high_signal(self):
        assert _is_high_signal({'role': 'user', 'message': 'about 80 dollars max'})

    def test_size_is_high_signal(self):
        assert _is_high_signal({'role': 'user', 'message': 'size M please'})

    def test_buy_phrase_is_high_signal(self):
        assert _is_high_signal({'role': 'user', 'message': "I'll take it"})

    def test_urgency_is_high_signal(self):
        assert _is_high_signal({'role': 'user', 'message': 'need it today urgently'})

    def test_filler_is_not_high_signal(self):
        assert not _is_high_signal({'role': 'user', 'message': 'ok thanks'})
        assert not _is_high_signal({'role': 'ai', 'message': 'Great! Anything else?'})

    def test_empty_message_is_not_high_signal(self):
        assert not _is_high_signal({'role': 'user', 'message': ''})
        assert not _is_high_signal({})


# ─── _select_recent_history ──────────────────────────────────────────────────

class TestSelectRecentHistory:
    def test_short_history_passes_through(self):
        history = [
            {'role': 'user', 'message': f'msg{i}'} for i in range(5)
        ]
        assert _select_recent_history(history) == history

    def test_empty_history_returns_empty(self):
        assert _select_recent_history([]) == []
        assert _select_recent_history(None) == []

    def test_window_trims_to_last_N(self):
        history = [
            {'role': 'user', 'message': f'plain message {i}'}
            for i in range(CHAT_HISTORY_WINDOW + 10)
        ]
        result = _select_recent_history(history)
        # All slots taken by the last CHAT_HISTORY_WINDOW (no high-signal
        # earlier msgs to promote).
        assert len(result) == CHAT_HISTORY_WINDOW
        assert result[-1] == history[-1]
        assert result[0] == history[-CHAT_HISTORY_WINDOW]

    def test_high_signal_older_msg_promoted(self):
        # Put an email at the very start — it should survive past the
        # verbatim window thanks to high-signal promotion.
        early_email = {'role': 'user', 'message': 'email is fred@example.com'}
        filler = [
            {'role': 'user', 'message': f'plain chatter {i}'}
            for i in range(CHAT_HISTORY_WINDOW + 5)
        ]
        history = [early_email] + filler
        result = _select_recent_history(history)
        # Promoted early msg sits at the front of the returned slice.
        assert result[0] == early_email
        # The verbatim tail is intact.
        assert result[-1] == history[-1]
        # Total never exceeds the hard cap.
        assert len(result) <= CHAT_HISTORY_HARD_CAP

    def test_hard_cap_enforced(self):
        # Many high-signal older msgs but we never exceed HARD_CAP.
        early_signal = [
            {'role': 'user', 'message': f'budget around ${100 + i}'}
            for i in range(50)
        ]
        recent = [
            {'role': 'user', 'message': f'tail {i}'}
            for i in range(CHAT_HISTORY_WINDOW)
        ]
        history = early_signal + recent
        result = _select_recent_history(history)
        assert len(result) <= CHAT_HISTORY_HARD_CAP


# ─── build_prompt summary injection ─────────────────────────────────────────

@pytest.mark.django_db
class TestBuildPromptSummaryBlock:
    def test_no_summary_means_no_block(self):
        sp, _, _, dyn = build_prompt(
            conversation_state='RESEARCH',
            context_chunks=[],
            behavior_matrix={},
            chat_history=[],
            user_message='hi',
            conversation_summary='',
        )
        assert 'EARLIER CONVERSATION SUMMARY' not in dyn
        assert 'EARLIER CONVERSATION SUMMARY' not in sp

    def test_summary_appears_in_dynamic_block(self):
        recap = 'Visitor is looking for a hoodie, budget around $80, size L.'
        sp, _, _, dyn = build_prompt(
            conversation_state='RESEARCH',
            context_chunks=[],
            behavior_matrix={},
            chat_history=[],
            user_message='hello',
            conversation_summary=recap,
        )
        assert 'EARLIER CONVERSATION SUMMARY' in dyn
        assert recap in dyn
        # Summary must precede the verbatim history block so the LLM reads
        # background before latest turns.
        assert dyn.index('EARLIER CONVERSATION SUMMARY') < dyn.index('RECENT CONVERSATION HISTORY')

    def test_summary_block_omitted_when_whitespace_only(self):
        _, _, _, dyn = build_prompt(
            conversation_state='RESEARCH',
            context_chunks=[],
            behavior_matrix={},
            chat_history=[],
            user_message='hi',
            conversation_summary='   \n\n',
        )
        assert 'EARLIER CONVERSATION SUMMARY' not in dyn

    def test_verbatim_history_window_used(self):
        # 30 messages → only the last CHAT_HISTORY_WINDOW reach the prompt
        # (no high-signal older msgs to promote).
        history = [
            {'role': 'user', 'message': f'simple chatter {i}'}
            for i in range(30)
        ]
        _, _, _, dyn = build_prompt(
            conversation_state='RESEARCH',
            context_chunks=[],
            behavior_matrix={},
            chat_history=history,
            user_message='ping',
        )
        # The very first plain msg shouldn't be in the rendered prompt.
        assert 'simple chatter 0' not in dyn
        # The most recent one must be.
        assert 'simple chatter 29' in dyn


# ─── truncate_chat_history pointer shift ────────────────────────────────────

@pytest.mark.django_db
class TestTruncatePointerShift:
    def test_pointer_shifts_left_by_archive_batch(self, chat_session):
        # Build a 250-message history with summary_through_index at 80.
        chat_session.chat_history = [
            {'role': 'user', 'message': f'm{i}'} for i in range(250)
        ]
        chat_session.summary_through_index = 80
        chat_session.save()

        fields = truncate_chat_history(chat_session)

        # 200 max, 50 archived → pointer should drop by 50.
        assert chat_session.summary_through_index == 30
        assert 'summary_through_index' in fields
        assert len(chat_session.chat_history) == 200

    def test_pointer_floor_is_zero(self, chat_session):
        # Pointer smaller than archive batch — must clamp to 0, not go negative.
        chat_session.chat_history = [
            {'role': 'user', 'message': f'm{i}'} for i in range(250)
        ]
        chat_session.summary_through_index = 10
        chat_session.save()

        truncate_chat_history(chat_session)
        assert chat_session.summary_through_index == 0

    def test_no_truncation_keeps_pointer(self, chat_session):
        chat_session.chat_history = [
            {'role': 'user', 'message': f'm{i}'} for i in range(50)
        ]
        chat_session.summary_through_index = 25
        chat_session.save()

        fields = truncate_chat_history(chat_session)
        assert chat_session.summary_through_index == 25
        assert 'summary_through_index' not in fields


# ─── maybe_schedule_summary ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestMaybeScheduleSummary:
    def test_below_threshold_does_not_enqueue(self, chat_session):
        from chat.tasks import maybe_schedule_summary, SUMMARY_TRIGGER_THRESHOLD
        chat_session.chat_history = [
            {'role': 'user', 'message': f'm{i}'}
            for i in range(SUMMARY_TRIGGER_THRESHOLD - 1)
        ]
        chat_session.summary_through_index = 0
        with patch('chat.tasks.summarize_chat_session.delay') as mock_delay:
            assert maybe_schedule_summary(chat_session) is False
            mock_delay.assert_not_called()

    def test_at_threshold_enqueues(self, chat_session):
        from chat.tasks import maybe_schedule_summary, SUMMARY_TRIGGER_THRESHOLD
        chat_session.chat_history = [
            {'role': 'user', 'message': f'm{i}'}
            for i in range(SUMMARY_TRIGGER_THRESHOLD)
        ]
        chat_session.summary_through_index = 0
        with patch('chat.tasks.summarize_chat_session.delay') as mock_delay:
            assert maybe_schedule_summary(chat_session) is True
            mock_delay.assert_called_once_with(str(chat_session.session_id))

    def test_already_summarised_tail_does_not_enqueue(self, chat_session):
        from chat.tasks import maybe_schedule_summary, SUMMARY_TRIGGER_THRESHOLD
        # 50 messages, summary already covers 45 → only 5 unsummarised.
        chat_session.chat_history = [
            {'role': 'user', 'message': f'm{i}'} for i in range(50)
        ]
        chat_session.summary_through_index = 45
        with patch('chat.tasks.summarize_chat_session.delay') as mock_delay:
            assert maybe_schedule_summary(chat_session) is False
            mock_delay.assert_not_called()


# ─── summarize_chat_session ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestSummarizeChatSession:
    def _fill_history(self, session, n=15):
        session.chat_history = []
        for i in range(n):
            session.chat_history.append({'role': 'user', 'message': f'visitor msg {i}'})
            session.chat_history.append({'role': 'ai', 'message': f'bot reply {i}'})
        session.save()

    def test_skips_when_no_session(self):
        from chat.tasks import summarize_chat_session
        import uuid as _uuid
        assert summarize_chat_session(str(_uuid.uuid4())) == 'no_session'

    def test_noop_when_threshold_not_met(self, chat_session):
        from chat.tasks import summarize_chat_session
        chat_session.chat_history = [
            {'role': 'user', 'message': 'one'},
            {'role': 'ai', 'message': 'two'},
        ]
        chat_session.summary_through_index = 0
        chat_session.save()
        # Under the threshold → noop.
        assert summarize_chat_session(str(chat_session.session_id)) == 'noop'
        chat_session.refresh_from_db()
        assert chat_session.conversation_summary == ''
        assert chat_session.summary_through_index == 0

    def test_updates_summary_and_advances_pointer(self, chat_session):
        from chat.tasks import summarize_chat_session

        self._fill_history(chat_session, n=15)
        before_len = len(chat_session.chat_history)

        fake_llm = MagicMock()
        fake_llm.invoke.return_value = MagicMock(content='Visitor wants a hoodie size L.')
        with patch('chat.ai_service._build_llm', return_value=(fake_llm, False)):
            result = summarize_chat_session(str(chat_session.session_id))

        assert result == 'updated'
        chat_session.refresh_from_db()
        assert chat_session.conversation_summary == 'Visitor wants a hoodie size L.'
        assert chat_session.summary_through_index == before_len

    def test_llm_failure_leaves_pointer_unchanged(self, chat_session):
        from chat.tasks import summarize_chat_session

        self._fill_history(chat_session, n=15)
        chat_session.summary_through_index = 0
        chat_session.save()

        fake_llm = MagicMock()
        fake_llm.invoke.side_effect = RuntimeError('LLM down')
        with patch('chat.ai_service._build_llm', return_value=(fake_llm, False)):
            result = summarize_chat_session(str(chat_session.session_id))

        assert result == 'llm_failed'
        chat_session.refresh_from_db()
        # Pointer untouched so a retry can fold the same slice.
        assert chat_session.summary_through_index == 0
        assert chat_session.conversation_summary == ''

    def test_summary_trimmed_to_max_chars(self, chat_session):
        from chat.tasks import summarize_chat_session, SUMMARY_MAX_CHARS

        self._fill_history(chat_session, n=15)

        long_text = 'word ' * 2000  # ~10,000 chars
        fake_llm = MagicMock()
        fake_llm.invoke.return_value = MagicMock(content=long_text)
        with patch('chat.ai_service._build_llm', return_value=(fake_llm, False)):
            summarize_chat_session(str(chat_session.session_id))

        chat_session.refresh_from_db()
        assert len(chat_session.conversation_summary) <= SUMMARY_MAX_CHARS + 1  # +1 for ellipsis

    def test_incremental_folds_only_new_messages(self, chat_session):
        """Second run should send only the messages added since the first run."""
        from chat.tasks import summarize_chat_session

        self._fill_history(chat_session, n=10)  # 20 messages total
        first_len = len(chat_session.chat_history)

        fake_llm = MagicMock()
        fake_llm.invoke.return_value = MagicMock(content='first summary')
        with patch('chat.ai_service._build_llm', return_value=(fake_llm, False)):
            summarize_chat_session(str(chat_session.session_id))

        chat_session.refresh_from_db()
        # Append 12 more messages, then re-run.
        for i in range(6):
            chat_session.chat_history.append({'role': 'user', 'message': f'new u{i}'})
            chat_session.chat_history.append({'role': 'ai', 'message': f'new a{i}'})
        chat_session.save()

        captured = {}
        def _capture(*args, **kwargs):
            captured['messages'] = args[0]
            return MagicMock(content='second summary')

        fake_llm2 = MagicMock()
        fake_llm2.invoke.side_effect = _capture
        with patch('chat.ai_service._build_llm', return_value=(fake_llm2, False)):
            summarize_chat_session(str(chat_session.session_id))

        # Second call should reference 'new u0'..'new u5' but NOT 'visitor msg 0'
        human_content = captured['messages'][1].content
        assert 'new u0' in human_content
        assert 'new u5' in human_content
        assert 'visitor msg 0' not in human_content
        # Pointer moved past everything.
        chat_session.refresh_from_db()
        assert chat_session.summary_through_index == len(chat_session.chat_history)


# ─── End-to-end: generate_ai_response schedules summariser ──────────────────

@pytest.mark.django_db
class TestGenerateResponseSchedulesSummary:
    def test_long_session_triggers_summariser_after_reply(self, chat_session):
        from chat.ai_service import generate_ai_response
        from chat.tasks import SUMMARY_TRIGGER_THRESHOLD

        # Pre-populate so the post-reply length crosses the threshold.
        chat_session.chat_history = [
            {'role': 'user', 'message': f'm{i}'}
            for i in range(SUMMARY_TRIGGER_THRESHOLD)
        ]
        chat_session.summary_through_index = 0
        chat_session.save()

        # Stub the LLM the chat path calls.
        ai_response = {
            'reply_text': 'Sure!',
            'intent_score': 0.5,
            'budget_score': 0.5,
            'urgency_score': 0.5,
        }
        fake_result = MagicMock(content=json.dumps(ai_response))
        fake_llm = MagicMock()
        fake_llm.invoke.return_value = fake_result

        fake_embedder = MagicMock()
        fake_embedder.embed_query.return_value = [0.0] * 1024

        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result), \
             patch('chat.ai_service.get_embeddings_model', return_value=fake_embedder), \
             patch('chat.tasks.summarize_chat_session.delay') as mock_delay:
            generate_ai_response(chat_session, 'hello there', behavior_matrix={})

        mock_delay.assert_called_once()
        assert str(chat_session.session_id) in str(mock_delay.call_args)

    def test_short_session_does_not_trigger_summariser(self, chat_session):
        from chat.ai_service import generate_ai_response

        chat_session.chat_history = []
        chat_session.summary_through_index = 0
        chat_session.save()

        ai_response = {
            'reply_text': 'hi!',
            'intent_score': 0.5,
            'budget_score': 0.5,
            'urgency_score': 0.5,
        }
        fake_result = MagicMock(content=json.dumps(ai_response))
        fake_embedder = MagicMock()
        fake_embedder.embed_query.return_value = [0.0] * 1024

        with patch('chat.ai_service._invoke_with_fallback', return_value=fake_result), \
             patch('chat.ai_service.get_embeddings_model', return_value=fake_embedder), \
             patch('chat.tasks.summarize_chat_session.delay') as mock_delay:
            generate_ai_response(chat_session, 'hi', behavior_matrix={})

        mock_delay.assert_not_called()

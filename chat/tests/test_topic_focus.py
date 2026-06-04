"""
Tests for topic-switch focus handling (Issue 2).

The bot used to stay stuck on the first-browsed product (dwell-sticky
top_interest). detect_current_focus reads the LATEST chat messages and the
prompt's CURRENT FOCUS block makes the model pivot.
"""
from types import SimpleNamespace

import pytest

from chat.ai_service import detect_current_focus
from chat.prompts import build_prompt


def _chunk(title, content='', url='https://x.com/p'):
    return SimpleNamespace(
        metadata={'title': title, 'type': 'product'},
        content=content or f'Product: {title}',
        source_url=url,
    )


def _session(history):
    return SimpleNamespace(chat_history=history)


class TestDetectCurrentFocus:
    def test_latest_message_pivot_wins(self):
        # Visitor browsed/asked about caps, now asks about hoodies.
        session = _session([
            {'role': 'user', 'message': 'how much is the cap'},
            {'role': 'ai', 'message': 'The Cap is රු16.00. For yourself or a gift?'},
        ])
        chunks = [_chunk('Cap'), _chunk('Hoodie with Zipper'), _chunk('Sunglasses')]
        focus = detect_current_focus(session, chunks, 'actually show me hoodies')
        assert focus == 'Hoodie with Zipper'

    def test_full_title_substring_beats_word(self):
        session = _session([])
        chunks = [_chunk('Hoodie with Zipper'), _chunk('Hoodie with Logo')]
        focus = detect_current_focus(session, chunks, 'I want the hoodie with logo please')
        assert focus == 'Hoodie with Logo'

    def test_no_match_returns_blank(self):
        session = _session([])
        chunks = [_chunk('Cap'), _chunk('Sunglasses')]
        focus = detect_current_focus(session, chunks, 'do you ship internationally?')
        assert focus == ''

    def test_empty_message_returns_blank(self):
        session = _session([])
        assert detect_current_focus(session, [_chunk('Cap')], '') == ''

    def test_current_message_outranks_prior_turn(self):
        # Prior user turn mentioned cap; current mentions hoodie → hoodie wins.
        session = _session([
            {'role': 'user', 'message': 'tell me about the cap'},
        ])
        chunks = [_chunk('Cap'), _chunk('Hoodie with Zipper')]
        focus = detect_current_focus(session, chunks, 'what about a hoodie')
        assert focus == 'Hoodie with Zipper'


@pytest.mark.django_db
class TestCurrentFocusInPrompt:
    def test_focus_block_rendered_and_authoritative(self):
        _, _, _, dyn = build_prompt(
            conversation_state='RESEARCH',
            context_chunks=[_chunk('Hoodie with Zipper')],
            behavior_matrix={'browsing_summary': {'top_interest': 'Cap'}},
            chat_history=[],
            user_message='show me hoodies',
            current_focus='Hoodie with Zipper',
        )
        assert 'CURRENT FOCUS' in dyn
        assert 'Hoodie with Zipper' in dyn
        assert 'OVERRIDES' in dyn
        # The focus block must come BEFORE the qualification checklist so the
        # model reads it first.
        assert dyn.index('CURRENT FOCUS') < dyn.index('QUALIFICATION CHECKLIST')

    def test_no_focus_block_when_blank(self):
        _, _, _, dyn = build_prompt(
            conversation_state='RESEARCH',
            context_chunks=[_chunk('Cap')],
            behavior_matrix={},
            chat_history=[],
            user_message='hi',
            current_focus='',
        )
        assert 'CURRENT FOCUS' not in dyn

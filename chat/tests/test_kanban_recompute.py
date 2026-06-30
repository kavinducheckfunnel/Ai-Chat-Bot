"""
Tests for chat.ai_service.compute_kanban_stage — the metric-driven stage
resolver used by the `recompute_kanban_states` backfill to move every lead to
its correct column based on heat / intent / urgency / messages.
"""
from types import SimpleNamespace

from chat.ai_service import compute_kanban_stage


def _s(kanban_state='NEW', intent=0.0, budget=0.0, urgency=0.0,
       message_count=0, conversation_state='RESEARCH'):
    return SimpleNamespace(
        kanban_state=kanban_state,
        current_intent_ema=intent,
        current_budget_ema=budget,
        current_urgency_ema=urgency,
        message_count=message_count,
        conversation_state=conversation_state,
    )


def test_no_engagement_stays_new():
    assert compute_kanban_stage(_s(message_count=0)) == 'NEW'


def test_message_moves_to_engaged():
    assert compute_kanban_stage(_s(message_count=2, intent=0.1)) == 'ENGAGED'


def test_intent_moves_to_qualified():
    assert compute_kanban_stage(_s(message_count=3, intent=0.65)) == 'QUALIFIED'


def test_high_heat_moves_to_hot_lead():
    # intent 0.9 → heat ≈ 0.9*0.45*100 = 40.5; add budget/urgency to clear 75.
    assert compute_kanban_stage(_s(message_count=3, intent=0.9, budget=0.9, urgency=0.9)) == 'HOT_LEAD'


def test_intent_urgency_combo_hot_lead():
    assert compute_kanban_stage(_s(message_count=1, intent=0.8, urgency=0.7)) == 'HOT_LEAD'


def test_ready_to_buy_from_conversation_state():
    assert compute_kanban_stage(_s(message_count=1, conversation_state='READY_TO_BUY')) == 'READY_TO_BUY'


def test_terminal_states_preserved():
    # Never auto-revert a converted / lost / ready card even with low metrics.
    assert compute_kanban_stage(_s(kanban_state='CONVERTED', message_count=0)) == 'CONVERTED'
    assert compute_kanban_stage(_s(kanban_state='LOST', message_count=0)) == 'LOST'
    assert compute_kanban_stage(_s(kanban_state='READY_TO_BUY', message_count=0)) == 'READY_TO_BUY'


def test_can_demote_overstated_stage():
    # A card sitting in HOT_LEAD with no supporting metrics recomputes down.
    assert compute_kanban_stage(_s(kanban_state='HOT_LEAD', message_count=1, intent=0.1)) == 'ENGAGED'

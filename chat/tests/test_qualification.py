"""
Tests for chat.qualification — the slot tracker that powers sales-enablement
behaviour. These cover the slot detectors (need / budget / urgency / variant /
delivery / contact) and the priority-ordering logic that decides what to ask
next.

The tests build lightweight stand-in objects with the same attribute surface
as ChatSession so we don't pay the cost of DB round-trips for what's really
a pure-function module.
"""

from types import SimpleNamespace

from chat.qualification import (
    detect_qualification,
    render_for_prompt,
    URGENCY_KEYWORDS,
    BUY_PHRASES,
)


def _mk_session(messages=None, lead_email='', lead_phone='',
                intent_ema=0.0, budget_ema=0.0, urgency_ema=0.0,
                heat_score=0, kanban_state='NEW', conversation_state='RESEARCH'):
    """Stub ChatSession with only the attrs the qualification module reads."""
    history = []
    for m in messages or []:
        if isinstance(m, str):
            history.append({'role': 'user', 'message': m})
        else:
            history.append(m)
    return SimpleNamespace(
        chat_history=history,
        lead_email=lead_email,
        lead_phone=lead_phone,
        current_intent_ema=intent_ema,
        current_budget_ema=budget_ema,
        current_urgency_ema=urgency_ema,
        heat_score=heat_score,
        kanban_state=kanban_state,
        conversation_state=conversation_state,
    )


# ── Slot detector tests ─────────────────────────────────────────────────────

class TestNeedDetection:
    def test_explicit_need_phrase_marks_filled(self):
        s = _mk_session(['I am looking for a hoodie'])
        q = detect_qualification(s)
        assert q.need_clear is True

    def test_high_intent_ema_implies_need(self):
        s = _mk_session(['hi'], intent_ema=0.4)
        q = detect_qualification(s)
        assert q.need_clear is True

    def test_two_user_turns_imply_need(self):
        s = _mk_session(['hi', 'hello again'])
        q = detect_qualification(s)
        assert q.need_clear is True

    def test_single_greeting_does_not_imply_need(self):
        s = _mk_session(['hi'])
        q = detect_qualification(s)
        assert q.need_clear is False


class TestBudgetDetection:
    def test_currency_symbol_detected(self):
        s = _mk_session(['my budget is $40'])
        q = detect_qualification(s)
        assert q.budget_clear is True
        assert '40' in q.detected_budget_mention or '$' in q.detected_budget_mention

    def test_textual_currency_detected(self):
        s = _mk_session(['around 1000 rupees would be ideal'])
        q = detect_qualification(s)
        assert q.budget_clear is True

    def test_range_detected(self):
        s = _mk_session(['something in the 40 to 60 range'])
        q = detect_qualification(s)
        assert q.budget_clear is True

    def test_no_budget_signal_keeps_slot_missing(self):
        s = _mk_session(['I want a hoodie for daily wear'])
        q = detect_qualification(s)
        assert q.budget_clear is False


class TestUrgencyDetection:
    def test_urgent_keyword_marks_filled_and_high(self):
        s = _mk_session(['I need this urgently'])
        q = detect_qualification(s)
        assert q.urgency_clear is True
        assert q.detected_urgency_mention in URGENCY_KEYWORDS

    def test_today_marks_urgent(self):
        s = _mk_session(['can I get it today?'])
        q = detect_qualification(s)
        assert q.urgency_clear is True

    def test_just_browsing_marks_slot_filled_not_urgent(self):
        # The slot is "answered" (we know they're not urgent), so we
        # shouldn't keep asking. detected_urgency_mention captures the negation.
        s = _mk_session(['just browsing thanks'])
        q = detect_qualification(s)
        assert q.urgency_clear is True
        assert 'browsing' in q.detected_urgency_mention.lower()

    def test_no_signal_keeps_missing(self):
        s = _mk_session(['I like the blue one'])
        q = detect_qualification(s)
        assert q.urgency_clear is False


class TestVariantDetection:
    def test_size_label_detected(self):
        s = _mk_session(['size M please'])
        q = detect_qualification(s)
        assert q.variant_specified is True

    def test_colour_detected(self):
        s = _mk_session(['I want the blue one'])
        q = detect_qualification(s)
        assert q.variant_specified is True


class TestDeliveryDetection:
    def test_ship_to_detected(self):
        s = _mk_session(['ship to Colombo please'])
        q = detect_qualification(s)
        assert q.delivery_given is True

    def test_pincode_phrase_detected(self):
        s = _mk_session(['my pincode is 560001'])
        q = detect_qualification(s)
        assert q.delivery_given is True


class TestContactDetection:
    def test_session_lead_email_marks_captured(self):
        s = _mk_session(['hi'], lead_email='kasun@example.com')
        q = detect_qualification(s)
        assert q.contact_captured is True

    def test_inline_email_in_chat_captured(self):
        s = _mk_session(['reach me at hello@example.com'])
        q = detect_qualification(s)
        assert q.contact_captured is True

    def test_inline_phone_in_chat_captured(self):
        s = _mk_session(['call me on +94 77 1234567'])
        q = detect_qualification(s)
        assert q.contact_captured is True

    def test_no_contact_remains_missing(self):
        s = _mk_session(['just looking around'])
        q = detect_qualification(s)
        assert q.contact_captured is False


class TestBuyingIntent:
    def test_explicit_buy_phrase(self):
        s = _mk_session(["I'll take it"])
        q = detect_qualification(s)
        assert q.buying_intent is True

    def test_ready_to_buy_state_implies_intent(self):
        s = _mk_session(['size M'], conversation_state='READY_TO_BUY')
        q = detect_qualification(s)
        assert q.buying_intent is True

    def test_high_intent_ema_implies_intent(self):
        s = _mk_session(['hmm'], intent_ema=0.8)
        q = detect_qualification(s)
        assert q.buying_intent is True


class TestHotLead:
    def test_heat_75_triggers_hot(self):
        s = _mk_session(['hi'], heat_score=80)
        q = detect_qualification(s)
        assert q.is_hot_lead is True

    def test_buying_intent_plus_no_contact_triggers_hot(self):
        s = _mk_session(["I'll take it"])
        q = detect_qualification(s)
        assert q.is_hot_lead is True

    def test_buying_intent_with_contact_NOT_hot(self):
        # If we already have contact, the "hot" flag is about closing
        # the gap — not relevant once contact is captured.
        s = _mk_session(["I'll take it"], lead_email='k@example.com')
        q = detect_qualification(s)
        assert q.is_hot_lead is False


# ── Priority ordering tests ─────────────────────────────────────────────────

class TestNextPrioritySlot:
    def test_fresh_session_asks_need_first(self):
        s = _mk_session(['hi'])
        q = detect_qualification(s)
        assert q.next_priority_slot() == 'NEED'

    def test_known_need_asks_budget_next(self):
        s = _mk_session(['I want a hoodie'])
        q = detect_qualification(s)
        assert q.next_priority_slot() == 'BUDGET'

    def test_need_and_budget_known_asks_urgency(self):
        s = _mk_session(['I want a hoodie under $50'])
        q = detect_qualification(s)
        assert q.next_priority_slot() == 'URGENCY'

    def test_all_but_contact_filled_asks_contact(self):
        s = _mk_session([
            'I want a hoodie under $50 in size M',
            'ship to Colombo, need it today',
        ])
        q = detect_qualification(s)
        assert q.next_priority_slot() == 'CONTACT'

    def test_everything_filled_returns_empty(self):
        s = _mk_session(
            ['I want a hoodie under $50 in size M, ship to Colombo, urgent'],
            lead_email='k@example.com',
        )
        q = detect_qualification(s)
        assert q.next_priority_slot() == ''


# ── Renderer tests ──────────────────────────────────────────────────────────

class TestRenderForPrompt:
    def test_renders_hot_lead_banner(self):
        s = _mk_session(["I'll take it"])
        block = render_for_prompt(detect_qualification(s))
        assert 'IS_HOT_LEAD: True' in block
        assert 'CAPTURE CONTACT NOW' in block

    def test_renders_filled_and_missing_markers(self):
        s = _mk_session(['I want a hoodie under $50'])
        block = render_for_prompt(detect_qualification(s))
        assert '✓ FILLED' in block
        assert '✗ MISSING' in block

    def test_renders_ema_snapshot(self):
        s = _mk_session(['hi'], intent_ema=0.42, budget_ema=0.1, urgency_ema=0.0)
        block = render_for_prompt(detect_qualification(s))
        assert 'intent=0.42' in block
        assert 'budget=0.1' in block

    def test_next_slot_line_present_when_missing(self):
        s = _mk_session(['hi'])
        block = render_for_prompt(detect_qualification(s))
        assert 'NEXT PRIORITY SLOT TO ASK: NEED' in block

    def test_completion_line_when_all_filled(self):
        s = _mk_session(
            ['I want a hoodie under $50 in size M, ship to Colombo, urgent'],
            lead_email='k@example.com',
        )
        block = render_for_prompt(detect_qualification(s))
        assert 'ALL SLOTS FILLED' in block


# ── Robustness: never crash on bad input ────────────────────────────────────

class TestRobustness:
    def test_empty_session(self):
        s = _mk_session([])
        q = detect_qualification(s)
        # Default state — everything missing, no crash
        assert q.need_clear is False
        assert q.is_hot_lead is False
        assert q.next_priority_slot() == 'NEED'

    def test_none_chat_history(self):
        s = _mk_session([])
        s.chat_history = None
        q = detect_qualification(s)
        assert q.need_clear is False  # no crash

    def test_messages_without_role_or_message_keys(self):
        s = _mk_session([{'foo': 'bar'}, {'role': 'ai', 'message': 'hi'}])
        q = detect_qualification(s)
        # Only counts user messages; ai messages ignored; no crash
        assert q.need_clear is False

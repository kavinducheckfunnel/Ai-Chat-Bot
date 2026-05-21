"""
Sales-qualification state tracker.

Reads the chat history + EMA scores + lead fields on a ChatSession and
derives WHICH qualification slots are filled vs missing. The output is
rendered into the LLM prompt under the "QUALIFICATION CHECKLIST" block so
the model always knows what to ASK NEXT instead of repeating questions or
staying in info-mode.

The slots match the BANT-style framework adapted for e-commerce:
    NEED      — visitor expressed what they're looking for (product type,
                use-case, recipient)
    BUDGET    — visitor mentioned price range OR comfort with displayed price
    URGENCY   — visitor mentioned timeline (today / this week / no rush)
    VARIANT   — size / colour / option specified when relevant
    DELIVERY  — delivery location / shipping area given
    CONTACT   — email or phone captured
    HOT_LEAD  — derived: heat_score≥75 OR (state==READY_TO_BUY AND missing
                contact)  → AI should capture contact in the next reply

Detection uses a mix of:
    1) Direct signals (session.lead_email / session.lead_phone)
    2) EMA score thresholds (intent / budget / urgency)
    3) Regex/keyword scans over the chat history

It is deliberately conservative — false negatives (an unfilled slot getting
asked) are OK, false positives (a slot marked filled that wasn't really)
are NOT, because the AI would skip the question and the visitor's data
never gets captured.
"""

import re
from dataclasses import dataclass, field, asdict


# ─────────────────────────────────────────────────────────────────────────────
# Detector patterns
# ─────────────────────────────────────────────────────────────────────────────

# Budget patterns: currency-prefixed numbers, ranges, "around X", "under X",
# explicit phrases like "my budget is" / "I can spend".
# Captures common currency symbols + textual mentions. False positives are
# acceptable here — at worst we skip asking budget once.
_BUDGET_RE = re.compile(
    r"""
    (?:                                                  # any of:
      (?:budget|spend|afford|price\s*range|under|below|
         around|about|roughly|max(?:imum)?|min(?:imum)?)  # explicit verbs
      .{0,30}?                                            # short gap
      \d                                                  # then a digit
    )
    |
    (?:[$£€₹¥]\s?\d)                                       # currency-prefixed
    |
    (?:                                                   # textual currency
      \d+\s*                                              # number first
      (?:dollars?|usd|rs\.?|rupees?|euros?|pounds?|inr|gbp)
    )
    |
    (?:                                                   # range like "40 to 60"
      \d+\s*(?:to|-|–)\s*\d+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Urgency patterns (also used as a manual score-boost signal in ai_service)
URGENCY_KEYWORDS = (
    'urgent', 'urgently', 'asap', 'as soon as possible', 'right away',
    'right now', 'immediately', 'today', 'tonight', 'this morning',
    'this afternoon', 'this evening', 'by tomorrow', 'tomorrow', 'rush',
    'in a hurry', 'priority', 'time sensitive', 'fast', 'quickly',
    'need it now', 'need it today', 'i need this',
)

# Phrases that explicitly indicate the visitor is just window-shopping —
# used to NEGATE urgency rather than confirm it.
_NO_URGENCY_PHRASES = (
    'just browsing', 'just looking', 'just exploring', 'no rush',
    'no hurry', 'not urgent', 'maybe later', 'thinking about',
)

# Need / use-case signals: phrases that show the visitor told us what they want.
_NEED_PHRASES = (
    'looking for', 'i need', 'i want', 'i\'m after', 'shopping for',
    'i\'d like', 'do you have', 'do you sell', 'show me',
    'recommend', 'suggest', 'best', 'for myself', 'for my', 'as a gift',
)

# Variant indicators — size labels, common colours, generic option words.
_VARIANT_RE = re.compile(
    r'\b('
    r'size\s+(?:xs|s|m|l|xl|xxl|\d+)'
    r'|size\s*[:=]?\s*\w+'
    r'|\b(?:xs|small|medium|large|xl|xxl)\b'
    r'|\b(?:red|blue|green|black|white|yellow|orange|pink|purple|grey|gray|brown)\b'
    r'|colou?r\s*[:=]?\s*\w+'
    r')\b',
    re.IGNORECASE,
)

# Delivery / shipping signals.
_DELIVERY_PHRASES = (
    'deliver to', 'shipping to', 'ship to', 'send to', 'address',
    'i live in', 'i\'m in', 'my address', 'pin code', 'pincode',
    'zip code', 'postcode', 'postal code', 'city of', 'in colombo',
    'in sri lanka', 'in india', 'in the uk', 'in the us',
)

# Phone-number pattern (loose — international shapes allowed).
_PHONE_RE = re.compile(r'(?:\+?\d[\s\-()]?){7,15}')

# Email pattern.
_EMAIL_RE = re.compile(r'[\w.+\-]+@[\w\-]+\.[\w.\-]+')

# Explicit "I want to buy / I'll take it" signals — used to detect buying intent.
BUY_PHRASES = (
    "i'll take it", 'i will take it', 'i\'ll buy', 'i want to buy',
    'i\'d like to buy', 'place the order', 'place an order',
    'ready to buy', 'ready to purchase', 'interested in buying',
    'how can i buy', 'how do i buy', 'how can i add it to cart',
    'how can i checkout', 'go ahead', 'sign me up', 'i\'m sold',
)


# ─────────────────────────────────────────────────────────────────────────────
# Data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class QualificationState:
    """A snapshot of what's qualified vs what's missing for one session."""
    need_clear:        bool = False
    budget_clear:      bool = False
    urgency_clear:     bool = False
    variant_specified: bool = False
    delivery_given:    bool = False
    contact_captured:  bool = False
    buying_intent:     bool = False
    is_hot_lead:       bool = False

    # Soft EMA snapshots (rounded) for the prompt
    intent_ema:   float = 0.0
    budget_ema:   float = 0.0
    urgency_ema:  float = 0.0

    # Detected fragments (helpful for the LLM to acknowledge without re-asking)
    detected_budget_mention: str = ''
    detected_urgency_mention: str = ''
    detected_variant_mention: str = ''
    detected_delivery_mention: str = ''

    def next_priority_slot(self):
        """Pick the highest-priority slot that's still missing.
        Order: NEED → BUDGET → URGENCY → VARIANT → DELIVERY → CONTACT.
        Returns the slot name or '' if everything's filled."""
        if not self.need_clear:        return 'NEED'
        if not self.budget_clear:      return 'BUDGET'
        if not self.urgency_clear:     return 'URGENCY'
        if not self.variant_specified: return 'VARIANT'
        if not self.delivery_given:    return 'DELIVERY'
        if not self.contact_captured:  return 'CONTACT'
        return ''


# ─────────────────────────────────────────────────────────────────────────────
# Detector
# ─────────────────────────────────────────────────────────────────────────────

def _user_messages(session):
    """All visitor messages concatenated, lowercased — cheap to scan."""
    history = getattr(session, 'chat_history', None) or []
    parts = []
    for msg in history:
        if msg.get('role') == 'user':
            text = msg.get('message') or msg.get('content') or ''
            if text:
                parts.append(text)
    return '\n'.join(parts).lower()


def _scan(pattern, text):
    """Helper — return first match group/string or '' if none."""
    if isinstance(pattern, re.Pattern):
        m = pattern.search(text)
        return m.group(0) if m else ''
    # pattern is a tuple/list of substrings
    for p in pattern:
        if p in text:
            return p
    return ''


def detect_qualification(session) -> QualificationState:
    """
    Build a QualificationState snapshot from the session's chat history
    + lead fields + EMA scores.

    Never raises — returns a default state on any error so the prompt
    builder can always render something.
    """
    state = QualificationState(
        intent_ema=round(getattr(session, 'current_intent_ema', 0.0), 2),
        budget_ema=round(getattr(session, 'current_budget_ema', 0.0), 2),
        urgency_ema=round(getattr(session, 'current_urgency_ema', 0.0), 2),
    )

    try:
        user_text = _user_messages(session)

        # ── NEED: explicit phrase OR intent EMA > 0.3 (visitor has expressed
        # something concrete) OR conversation has at least 2 user turns
        history = getattr(session, 'chat_history', None) or []
        user_turn_count = sum(1 for m in history if m.get('role') == 'user')
        need_phrase = _scan(_NEED_PHRASES, user_text)
        state.need_clear = bool(
            need_phrase or state.intent_ema >= 0.3 or user_turn_count >= 2
        )

        # ── BUDGET
        budget_match = _scan(_BUDGET_RE, user_text)
        state.budget_clear = bool(budget_match) or state.budget_ema >= 0.7
        state.detected_budget_mention = budget_match[:80] if budget_match else ''

        # ── URGENCY (positive signal beats negative)
        urgency_match = _scan(URGENCY_KEYWORDS, user_text)
        negation_match = _scan(_NO_URGENCY_PHRASES, user_text)
        if urgency_match:
            state.urgency_clear = True
            state.detected_urgency_mention = urgency_match
        elif negation_match:
            # Visitor explicitly said "just browsing" — slot IS clarified,
            # they're not urgent. Don't ask again.
            state.urgency_clear = True
            state.detected_urgency_mention = negation_match
        elif state.urgency_ema >= 0.7:
            state.urgency_clear = True

        # ── VARIANT (size / colour / option)
        variant_match = _scan(_VARIANT_RE, user_text)
        state.variant_specified = bool(variant_match)
        state.detected_variant_mention = variant_match[:60] if variant_match else ''

        # ── DELIVERY
        delivery_match = _scan(_DELIVERY_PHRASES, user_text)
        state.delivery_given = bool(delivery_match)
        state.detected_delivery_mention = delivery_match[:80] if delivery_match else ''

        # ── CONTACT (most reliable signals first)
        # Direct fields on the session take priority — they're set by the
        # widget's lead modal POST /api/chat/lead/. Inline pattern matches
        # in chat history act as a fallback when the visitor types contact
        # details mid-conversation before the modal even opens.
        lead_email_raw = getattr(session, 'lead_email', '') or ''
        lead_phone_raw = getattr(session, 'lead_phone', '') or ''
        has_lead_email = bool(lead_email_raw.strip() if isinstance(lead_email_raw, str) else lead_email_raw)
        has_lead_phone = bool(lead_phone_raw.strip() if isinstance(lead_phone_raw, str) else lead_phone_raw)
        inline_email = bool(_EMAIL_RE.search(user_text))
        inline_phone = bool(_PHONE_RE.search(user_text))
        state.contact_captured = bool(has_lead_email or has_lead_phone or inline_email or inline_phone)

        # ── BUYING INTENT
        buy_phrase_match = _scan(BUY_PHRASES, user_text)
        state.buying_intent = bool(
            buy_phrase_match
            or state.intent_ema >= 0.75
            or getattr(session, 'conversation_state', '') == 'READY_TO_BUY'
        )

        # ── HOT LEAD: heat score crossed OR buying intent + contact still missing
        heat = getattr(session, 'heat_score', 0) or 0
        state.is_hot_lead = bool(
            heat >= 75
            or (state.buying_intent and not state.contact_captured)
        )

    except Exception:
        # Best-effort: never break the prompt build over a detector bug.
        pass

    return state


# ─────────────────────────────────────────────────────────────────────────────
# Renderer — turns QualificationState into a prompt block
# ─────────────────────────────────────────────────────────────────────────────

def render_for_prompt(state: QualificationState) -> str:
    """
    Renders the qualification snapshot as a readable checklist for the LLM.
    The format is deliberately verbose so a smaller LLM still picks up the
    signal — explicit ✓ / ✗ markers and a final "NEXT SLOT TO ASK" line.
    """
    def mark(filled): return '✓ FILLED ' if filled else '✗ MISSING'

    next_slot = state.next_priority_slot()
    hot = ' >>> HOT LEAD — CAPTURE CONTACT NOW <<<' if state.is_hot_lead else ''

    lines = [
        f"IS_HOT_LEAD: {state.is_hot_lead}{hot}",
        f"BUYING_INTENT_DETECTED: {state.buying_intent}",
        '',
        f"  {mark(state.need_clear)}  NEED       — what they're looking for",
        f"  {mark(state.budget_clear)}  BUDGET     — price comfort"
        + (f"  (mentioned: '{state.detected_budget_mention}')" if state.detected_budget_mention else ''),
        f"  {mark(state.urgency_clear)}  URGENCY    — timeline"
        + (f"  (mentioned: '{state.detected_urgency_mention}')" if state.detected_urgency_mention else ''),
        f"  {mark(state.variant_specified)}  VARIANT    — size / colour / option"
        + (f"  (mentioned: '{state.detected_variant_mention}')" if state.detected_variant_mention else ''),
        f"  {mark(state.delivery_given)}  DELIVERY   — shipping area"
        + (f"  (mentioned: '{state.detected_delivery_mention}')" if state.detected_delivery_mention else ''),
        f"  {mark(state.contact_captured)}  CONTACT    — email or phone",
        '',
        f"EMA SNAPSHOT: intent={state.intent_ema}  budget={state.budget_ema}  urgency={state.urgency_ema}",
    ]
    if next_slot:
        lines.append('')
        lines.append(f"NEXT PRIORITY SLOT TO ASK: {next_slot}")
        lines.append("→ End your reply with ONE question that fills this slot. "
                     "If IS_HOT_LEAD, combine the missing slots into a single "
                     "natural ask (size + delivery + contact).")
    else:
        lines.append('')
        lines.append("ALL SLOTS FILLED — confirm the lead and name the follow-up window.")
    return "\n".join(lines)


def build_qualification_block(session) -> str:
    """Convenience: detect + render in one call. Used by ai_service.py."""
    return render_for_prompt(detect_qualification(session))

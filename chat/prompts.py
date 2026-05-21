import json

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PERSONA  (injected into every request)
#
# This persona is engineered for SALES ENABLEMENT behaviour first, not Q/A.
# The bot's job is to MOVE A VISITOR DOWN THE FUNNEL:
#     browsing → discovering → qualifying → closing → lead-captured
# It must consistently ASK qualifying questions, not just answer.
# Behaviour adapts to the conversation_state (RESEARCH/EVALUATION/OBJECTION/
# RECOVERY/READY_TO_BUY) and to the I/B/U EMA scores injected via the
# QUALIFICATION CHECKLIST block.
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PERSONA = """
You are a Sales Enablement Assistant for this website — NOT a generic Q/A bot.

Your job is to MOVE every conversation toward a closed lead. You do that by:
  1. Answering accurately from the knowledge base, briefly
  2. Asking ONE qualifying question after every substantive answer
  3. Capturing the lead the moment buying intent is clear

Tone: friendly, direct, human. Brief. No filler ("Great question!", "You're
going to love this!"). Vary your wording — never sound robotic.

════════════════════════════════════════
CORE SALES PLAYBOOK (apply on every reply)
════════════════════════════════════════

PLAYBOOK STEP 1 — ANSWER (concise, ≤ 2 sentences for non-list answers).
  Pull facts from the PRODUCT / CONTENT KNOWLEDGE BASE only. Never invent
  product names, prices, URLs, or features.

PLAYBOOK STEP 2 — QUALIFY (always end with ONE question, unless the visitor
  has just said something that closes the conversation — see STEP 4).
  The question depends on what's MISSING from the QUALIFICATION CHECKLIST:
    • Need not yet clear  → ask use-case / preference
    • Budget not yet clear → ask range
    • Urgency not yet clear → ask timeline ("Looking to buy soon, or
      just exploring?")
    • Size/variant not specified → ask
    • Delivery location not given (when state is EVALUATION or higher) → ask
  Never ask more than ONE question per reply. Never ask a question the
  visitor has already answered.

PLAYBOOK STEP 3 — RECOMMEND (when the visitor's need is clear).
  Recommend ONE best-fit option with a one-line reason, optionally a second
  alternative. Do NOT dump the whole catalog. End with a decision-ready
  question: "Want me to check availability for size M?" / "Shall I share
  the pricing breakdown?"

PLAYBOOK STEP 4 — CLOSE (when the visitor signals buying intent).
  Buying-intent signals: "I'll take it", "interested in buying", "place
  the order", "ready to buy", "I need this urgently", "can I get it today",
  any explicit ask to purchase, or a clear add-to-cart-related question.
  When detected:
    a) Confirm the choice in ONE sentence ("Great — the Hoodie with
       Zipper in M.")
    b) Capture what's still missing in priority order: size/variant →
       delivery location → contact (phone or email).
    c) Phrase the ask as a single combined sentence:
       "To lock this in, could you share your size, delivery area,
       and the best number to reach you?"
    d) When the visitor gives ANY contact info, confirm it back:
       "Got it. I've marked this as a priority lead — our team will
       reach you within X hours about <product>."

PLAYBOOK STEP 5 — URGENCY HANDLING (whenever the visitor says
  "urgently", "today", "asap", "now", "right away", "fast", or "rush"):
    • DO NOT just give checkout instructions
    • DO ask immediately for delivery area + phone number
    • Acknowledge urgency in your wording ("For same-day delivery…")

PLAYBOOK STEP 6 — OBJECTION HANDLING (when budget concern appears):
    • Don't push the original recommendation
    • Offer the closest cheaper alternative from the knowledge base
    • Frame as choice: "If price matters most, X is the value pick.
      If quality matters most, Y. Which feels right?"

════════════════════════════════════════
STRICT RULES (non-negotiable)
════════════════════════════════════════

RULE A — LENGTH.
  • Non-list answers: 1–3 sentences. NEVER paragraphs.
  • List answers: max 5 items unless the visitor explicitly asks for more.
  • Always leave room for the qualifying question (PLAYBOOK STEP 2).

RULE B — LIST FORMATTING.
  When listing products, articles, or tools, each item MUST be on its
  own line in this exact shape:

      1. [Item Name](SOURCE_URL) — one-line benefit
      2. [Item Name](SOURCE_URL) — one-line benefit

  Each item on a NEW LINE. Never merge multiple items into one line.
  After any list, append ONE qualifying question on a fresh line.

RULE C — GREETINGS (when the visitor's message is "hi", "hello", "hey"
  or similar and they have NOT yet asked anything):
  Reply warmly in 1–2 sentences. Introduce yourself briefly. End with a
  scoping question: "Are you shopping for yourself, a gift, or just
  exploring today?"
  Do NOT search the knowledge base on a greeting.

RULE D — ALWAYS USE THE KNOWLEDGE BASE.
  • The [Source Title] in each chunk IS the product/article name. Use it.
  • Even if a chunk starts mid-sentence, include the item if relevant.
  • NEVER invent product names, prices, or URLs not in the chunks.
  • NEVER use external URLs — only this website's URLs.

RULE E — LINKS.
  Every item in a list MUST have its own inline link. No shared "Source:"
  footer. Only URLs from the knowledge chunks. If a chunk doesn't have
  a URL → don't link.

RULE F — COUNT.
  If the visitor asks for N items ("5 tools", "top 3"), return exactly N
  numbered items unless the KB genuinely has fewer.

RULE G — STATE-AWARE BEHAVIOUR.
  Read YOUR CURRENT SALES STRATEGY (below). Apply its playbook on top of
  the core playbook. Higher-intent states REQUIRE closer-to-the-close
  behaviour — never stay in info-mode when state == READY_TO_BUY.

RULE H — BROWSING-CONTEXT OPENING (use sparingly, only on the FIRST
  message of the session and ONLY if the visitor sent a generic greeting
  AND there's a clear TOP INTEREST with ≥10s dwell):
    GOOD: "Hey! Saw you were checking out [Product] — anything you'd
           like to know?"
    BAD : Quoting exact dwell times, mentioning every page viewed,
          referencing browsing on a non-first message.
  If TOP INTEREST is missing or dwell <10s, greet normally — do NOT
  fabricate context.

RULE I — HOT-LEAD MODE.
  When QUALIFICATION CHECKLIST shows IS_HOT_LEAD: true, you MUST capture
  contact info in your next reply if any of phone/email is missing.
  Phrase it confidently as a next step, not a survey.

RULE J — NEVER DEFLECT.
  • Don't say "I'll connect you to a team member" unless the visitor
    explicitly asks for human help.
  • Don't say "please visit our contact page" — instead, capture their
    details and tell them the team will reach them.
  • Don't say "I don't have a full list" — combine what's in the KB and
    answer.

RULE K — STRUCTURED OUTPUT (machine).
  Always score the visitor's CURRENT message on:
    intent_score   (0.0–1.0): how strongly do they want to buy/use?
    budget_score   (0.0–1.0): are they comfortable with pricing?
    urgency_score  (0.0–1.0): how urgently do they need this?
  Be honest — a casual browser is 0.3, a "I'll take it" is 0.95.
  Urgency words like "today", "urgent", "asap" → urgency_score ≥ 0.8.
"""

# ─────────────────────────────────────────────────────────────────────────────
# STATE-SPECIFIC PLAYBOOKS
#
# Each playbook below tells the AI what to PRIORITIZE in that state, what
# question to ask next, and what NOT to do. Expanded from one-liners so
# the model has concrete behaviour, not vibes.
# ─────────────────────────────────────────────────────────────────────────────

STATE_INSTRUCTIONS = {
    'RESEARCH': (
        "STATE = RESEARCH (visitor is exploring).\n"
        "GOAL: surface relevant options + start qualifying.\n"
        "DO:\n"
        "  • Give a brief, accurate answer from the knowledge base.\n"
        "  • End with ONE discovery question: who is this for? "
        "use-case? size/variant preference?\n"
        "DON'T:\n"
        "  • Dump the whole catalog.\n"
        "  • Stay neutral when the visitor is clearly interested — push "
        "to EVALUATION with a recommendation."
    ),
    'EVALUATION': (
        "STATE = EVALUATION (visitor is comparing options).\n"
        "GOAL: narrow the choice + surface a budget/timeline signal.\n"
        "DO:\n"
        "  • Compare 2 options factually (price, key feature, who it's for).\n"
        "  • Recommend ONE best-fit with one-line reason.\n"
        "  • Ask: 'Looking to buy soon, or just narrowing the list?'\n"
        "DON'T:\n"
        "  • List >3 alternatives — pick the best.\n"
        "  • Re-explain category basics; assume they're past that."
    ),
    'OBJECTION': (
        "STATE = OBJECTION (budget concern OR hesitation).\n"
        "GOAL: handle the concern + present a value-based alternative.\n"
        "DO:\n"
        "  • Acknowledge the concern in 1 sentence.\n"
        "  • Offer the closest cheaper alternative from the KB, OR frame "
        "the value of the current pick (ROI / durability / inclusions).\n"
        "  • Ask: 'Is price the main factor, or is it about <feature>?'\n"
        "DON'T:\n"
        "  • Push the original product harder.\n"
        "  • Ignore the objection."
    ),
    'RECOVERY': (
        "STATE = RECOVERY (visitor cooled off, now warming back up).\n"
        "GOAL: re-engage with what they were last interested in.\n"
        "DO:\n"
        "  • Reference the TOP INTEREST or last-discussed product by name.\n"
        "  • Restate ONE concrete benefit.\n"
        "  • Ask a low-pressure next-step question.\n"
        "DON'T:\n"
        "  • Apologize or grovel ('Sorry to bother you…').\n"
        "  • Re-do discovery questions they already answered."
    ),
    'READY_TO_BUY': (
        "STATE = READY_TO_BUY (high intent, time to close).\n"
        "GOAL: capture missing details (size, delivery, contact) and close.\n"
        "DO:\n"
        "  • Confirm the product in ONE sentence.\n"
        "  • Capture the remaining slot(s) from the qualification checklist "
        "in a single combined ask.\n"
        "  • Once any contact info arrives → confirm the lead is saved and "
        "name a follow-up window ('our team will reach you within X hours').\n"
        "DON'T:\n"
        "  • Stay in info-mode (no more 'here are the variants').\n"
        "  • Send the visitor away to a contact page — capture here."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# BROWSING-CONTEXT FORMATTER
# (unchanged from prior version — already produces good narrative for the LLM)
# ─────────────────────────────────────────────────────────────────────────────

def _format_browsing_context(behavior_matrix):
    """Render the enriched browsing_summary as a readable narrative."""
    bs = (behavior_matrix or {}).get('browsing_summary') or {}
    if not bs.get('pages') and not bs.get('signals'):
        return "(no prior browsing data captured)"

    lines = []
    if bs.get('is_first_msg'):
        lines.append(">> This is the visitor's FIRST message in the session <<")
        lines.append("")

    if bs.get('top_interest'):
        dwell = bs.get('top_interest_dwell', 0)
        mins, secs = divmod(dwell, 60)
        t = f"{mins}m {secs}s" if mins else f"{secs}s"
        url = bs.get('top_interest_url') or ''
        lines.append(f"TOP INTEREST: {bs['top_interest']} ({t} dwell)")
        if url:
            lines.append(f"  → URL: {url}")

    pages = bs.get('pages') or []
    if pages:
        lines.append("")
        lines.append("RECENT PAGES VIEWED (oldest → newest):")
        for p in pages:
            secs = p.get('dwell_seconds', 0)
            mins, ss = divmod(secs, 60)
            t = f"{mins}m {ss}s" if mins else f"{secs}s"
            tag = " [PRODUCT]" if p.get('is_product') else ""
            lines.append(f"  • {p.get('title', 'Unknown')} — {t}{tag}")

    signals = bs.get('signals') or []
    if signals:
        lines.append("")
        lines.append("BEHAVIORAL SIGNALS:")
        for s in signals:
            lines.append(f"  • {s}")

    lines.append("")
    lines.append(f"INTENT HEAT LEVEL: {bs.get('heat_level', 'LOW')}")
    if bs.get('is_returning'):
        lines.append("RETURNING VISITOR (they've been here before)")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(
    conversation_state,
    context_chunks,
    behavior_matrix,
    chat_history,
    user_message,
    website_domain="",
    qualification_block="",
):
    """
    Build the full system + user prompt pair.

    qualification_block: rendered text from chat.qualification.render_for_prompt()
    that tells the LLM what's been qualified (need/budget/urgency/size/contact)
    and what's still missing. This is the single biggest sales-enablement
    upgrade — without it the LLM has no idea what to ASK NEXT.
    """
    state_instruction = STATE_INSTRUCTIONS.get(conversation_state, STATE_INSTRUCTIONS['RESEARCH'])

    # Build context blocks — each chunk clearly labelled with its title + URL
    context_blocks = []
    for chunk in context_chunks:
        meta = chunk.metadata if isinstance(chunk.metadata, dict) else {}
        title = meta.get('title', 'Unknown')
        url = chunk.source_url or 'N/A'
        context_blocks.append(
            f"[Source Title: {title}]\n[Source URL: {url}]\n{chunk.content}"
        )

    context_text = "\n\n---\n\n".join(context_blocks) if context_blocks else "No relevant content found."

    # Trim chat history to last 6 exchanges to keep context manageable
    recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history

    # Render browsing context as readable narrative for natural AI responses
    browsing_block = _format_browsing_context(behavior_matrix)

    system_prompt = f"""{SYSTEM_PERSONA}

════════════════════
WEBSITE DOMAIN: {website_domain}
════════════════════

YOUR CURRENT SALES STRATEGY:
{state_instruction}

════════════════════
QUALIFICATION CHECKLIST
(What you already know about this visitor vs. what's still missing.
Use this to decide what to ask next — never re-ask a slot already filled.)
════════════════════
{qualification_block or '(no qualification data yet — treat this as the start of discovery)'}

════════════════════
PRODUCT / CONTENT KNOWLEDGE BASE
(Use ONLY this data to answer — do not hallucinate)
════════════════════
{context_text}

════════════════════
VISITOR BROWSING CONTEXT
(What this person did on the site BEFORE opening chat — reference naturally per RULE H)
════════════════════
{browsing_block}

════════════════════
RECENT CONVERSATION HISTORY
════════════════════
{json.dumps(recent_history, indent=2)}
"""

    # ── Inject high-salience opening hint for greeting + browsing context ──
    bs = (behavior_matrix or {}).get('browsing_summary') or {}
    msg_lower = (user_message or '').lower().strip()
    is_greeting = msg_lower in {'hi', 'hello', 'hey', 'yo', 'sup', 'hii', 'helo', 'howdy'} or \
                  any(msg_lower.startswith(g) for g in ['hi ', 'hello ', 'hey ', 'good morning', 'good evening', 'good afternoon'])

    if bs.get('is_first_msg') and bs.get('top_interest') and is_greeting:
        opening_hint = (
            f"\n\n>>> SYSTEM HINT (MUST FOLLOW): This visitor's FIRST message is a greeting, "
            f"and they were just looking at \"{bs['top_interest']}\" on the site "
            f"({bs.get('top_interest_dwell', 0)}s dwell). "
            f"Your reply MUST acknowledge this in a natural, friendly way — e.g. "
            f"\"Hey! Saw you were checking out {bs['top_interest']} — anything you want to know?\" "
            f"Then ask ONE scoping question (for yourself / a gift / just exploring). "
            f"Do NOT quote dwell time. Vary the wording. <<<"
        )
        user_prompt = f"User message: {user_message}{opening_hint}"
    else:
        user_prompt = f"User message: {user_message}"

    return system_prompt, user_prompt


# ─────────────────────────────────────────────────────────────────────────────
# STRUCTURED OUTPUT SCHEMA  (for DeepSeek / Gemini / Bedrock structured mode)
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_SCHEMA = {
    "title": "SalesInteraction",
    "type": "object",
    "properties": {
        "reply_text": {
            "type": "string",
            "description": (
                "Your conversational reply. Short — 1-3 sentences for an answer, "
                "or a numbered list for tool requests. Apply the SALES PLAYBOOK: "
                "answer briefly, then ask ONE qualifying question (unless the "
                "visitor explicitly closed the conversation). "
                "CRITICAL for lists: each item MUST start on a new line:\n"
                "1. [Name](URL) — benefit\n2. [Name](URL) — benefit\n"
                "Only use real URLs from the knowledge base. No filler openers."
            )
        },
        "intent_score": {
            "type": "number",
            "description": "How strongly does the user want to buy/use? 0.0=casual browser, 0.5=interested, 0.9=ready to buy."
        },
        "budget_score": {
            "type": "number",
            "description": "Is the user comfortable with our pricing? 0.0=sticker shock, 0.5=neutral, 0.9=comfortable."
        },
        "urgency_score": {
            "type": "number",
            "description": "How urgently do they need a solution? 0.0=no rush, 0.5=normal, 0.9=today/urgent/asap."
        },
        "suggested_product_id": {
            "type": "integer",
            "description": "WordPress post/product ID to show as a card, or null if none."
        }
    },
    "required": ["reply_text", "intent_score", "budget_score", "urgency_score"]
}

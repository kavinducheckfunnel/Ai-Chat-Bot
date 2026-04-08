import json

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PERSONA  (injected into every request)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PERSONA = """
You are a friendly, concise AI assistant for this website. You're helpful and human — but always brief.

Tone: friendly and direct. No filler phrases like "Great question!" or "You're going to love this!". Just give the answer.

════════════════════════════════════════
CRITICAL RESPONSE RULES (follow exactly)
════════════════════════════════════════

RULE 0 — LENGTH LIMIT (highest priority).
• For non-list answers: max 2–3 sentences. No paragraphs.
• For list answers: max 5 items unless the user explicitly asks for more.
• NEVER write a long preamble before a list. Jump straight to the list.

RULE 1 — LIST FORMATTING (mandatory).
When listing tools or items, EVERY item MUST be on its own separate line, exactly like this:

1. [Tool Name](SOURCE_URL) — one-line benefit
2. [Tool Name](SOURCE_URL) — one-line benefit
3. [Tool Name](SOURCE_URL) — one-line benefit

Each item on a NEW LINE. No exceptions. Do NOT put multiple items on one line.

RULE 2 — GREETINGS.
If the user says "hi", "hello", "how are you", or any casual greeting → reply warmly in 1–2 sentences, introduce yourself, and invite them to ask a question. Do NOT search for products.

RULE 3 — ALWAYS ANSWER FROM THE KNOWLEDGE BASE.
If the user asks about tools, tips, articles, or topics → scan ALL provided knowledge chunks.
• The [Source Title] in each chunk IS the tool/article name — use it directly.
• Even if a chunk starts mid-sentence, include the tool if its title or content is relevant.
• LinkedIn tools, Instagram tools, scheduling tools, content tools etc. ALL count as "social media" tools.
• DO NOT say "I don't have a full list" — if items exist across chunks, combine them.
• NEVER ask "would you like me to list them?" — just give the list immediately.
• NEVER invent tool names or URLs not in the knowledge base chunks.

RULE 4 — LINK RULES.
SOURCE_URL rules (in priority order):
  a) If the tool has its own dedicated page in the knowledge base → use that page's Source URL.
  b) If the tool is mentioned in a roundup/listicle article → use that article's Source URL.
  c) NEVER leave a tool without a link.
  d) NEVER use a shared "📖 Source:" citation at the bottom — every item gets its OWN inline link.
  e) NEVER invent URLs. ONLY use Source URLs from the knowledge chunks.
  f) NEVER use external URLs (e.g. openai.com, midjourney.com) — only this website's URLs.

RULE 5 — WEBSITE NAME.
If asked "what is this website?" → look at WEBSITE DOMAIN and answer naturally in 1 sentence.

RULE 6 — AGGREGATE.
If asked for 5 items and they're spread across 3 chunks, combine them all into one numbered list.

RULE 7 — COUNT RULE.
If the user asks for N tools (e.g. "5 tools", "top 3 tools"), return exactly N numbered items.
NEVER return fewer items than requested unless the knowledge base genuinely has fewer.

RULE 8 — SCORING AWARENESS.
If intent_level is "High-Intent Lead", be direct and action-oriented. End with one clear CTA link — nothing else.
"""

# ─────────────────────────────────────────────────────────────────────────────
# STATE-SPECIFIC SALES STRATEGIES
# ─────────────────────────────────────────────────────────────────────────────

STATE_INSTRUCTIONS = {
    'RESEARCH': (
        "The user is exploring. Answer their question directly from the knowledge base. "
        "Do NOT gatekeep information. Do NOT ask if they want the list — just give it."
    ),
    'EVALUATION': (
        "The user is comparing options. Highlight what makes the items in our knowledge base "
        "stand out. Keep comparisons brief and factual."
    ),
    'OBJECTION': (
        "The user has concerns (e.g. about price or value). Address the concern directly "
        "with facts from the knowledge base. Focus on ROI and real benefits."
    ),
    'RECOVERY': (
        "The user is warming back up. Reinforce the value of what they were looking at. "
        "Be warm and helpful."
    ),
    'READY_TO_BUY': (
        "The user is ready to act. Stop explaining features. "
        "Give them a clear, direct call-to-action with the relevant link."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(conversation_state, context_chunks, behavior_matrix, chat_history, user_message, website_domain=""):
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

    system_prompt = f"""{SYSTEM_PERSONA}

════════════════════
WEBSITE DOMAIN: {website_domain}
════════════════════

YOUR CURRENT SALES STRATEGY:
{state_instruction}

════════════════════
PRODUCT / CONTENT KNOWLEDGE BASE
(Use ONLY this data to answer — do not hallucinate)
════════════════════
{context_text}

════════════════════
USER BEHAVIOUR (silent browsing before this chat)
════════════════════
{json.dumps(behavior_matrix, indent=2)}

════════════════════
RECENT CONVERSATION HISTORY
════════════════════
{json.dumps(recent_history, indent=2)}
"""

    user_prompt = f"User message: {user_message}"

    return system_prompt, user_prompt


# ─────────────────────────────────────────────────────────────────────────────
# STRUCTURED OUTPUT SCHEMA  (DeepSeek / Bedrock)
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_SCHEMA = {
    "title": "SalesInteraction",
    "type": "object",
    "properties": {
        "reply_text": {
            "type": "string",
            "description": (
                "Your conversational reply. Keep it SHORT — max 2-3 sentences for answers, "
                "or a numbered list for tool requests. "
                "CRITICAL for lists: each item MUST start on a new line like:\n"
                "1. [Name](URL) — benefit\n2. [Name](URL) — benefit\n"
                "Only use real URLs from the knowledge base. No filler openers."
            )
        },
        "intent_score": {
            "type": "number",
            "description": "How strongly does the user want to buy/use something? (0.0 – 1.0)"
        },
        "budget_score": {
            "type": "number",
            "description": "Is the user comfortable with the pricing / investment? (0.0 – 1.0)"
        },
        "urgency_score": {
            "type": "number",
            "description": "How urgently does the user need a solution? (0.0 – 1.0)"
        },
        "suggested_product_id": {
            "type": "integer",
            "description": "WordPress post/product ID to show as a card, or null if none."
        }
    },
    "required": ["reply_text", "intent_score", "budget_score", "urgency_score"]
}

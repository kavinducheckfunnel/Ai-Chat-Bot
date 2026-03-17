import json

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PERSONA  (injected into every request)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PERSONA = """
You are a warm, enthusiastic AI assistant for this website — like a knowledgeable friend who has read every article and review on the site. You're upbeat, approachable, and genuinely excited to help people find the right tools and tips.

Tone: conversational, encouraging, never robotic. Use phrases like "Great question!", "You're going to love this one!", "Here's what I found for you:" to make responses feel human and friendly.

════════════════════════════════════════
CRITICAL RESPONSE RULES (follow exactly)
════════════════════════════════════════

RULE 1 — BE WARM BUT CONCISE.
Keep answers short and energetic. Add a brief friendly opener (1 sentence). Then give the list or answer. End with an encouraging closer like "Let me know if you want more details on any of these! 😊"

RULE 2 — GREETINGS.
If the user says "hi", "hello", "how are you", or any casual greeting → respond warmly in plain text, introduce yourself, and invite them to ask a question. Do NOT search for products.

RULE 3 — ALWAYS ANSWER FROM THE KNOWLEDGE BASE.
If the user asks about tools, tips, articles, or topics → search through ALL provided knowledge chunks.
• DO NOT say "I don't have a full list" — if items are scattered across chunks, combine them.
• NEVER ask "would you like me to list them?" — just give the list immediately.
• NEVER hallucinate tools, URLs, or names not in the knowledge base.

RULE 4 — CLICKABLE LINKS (CRITICAL — READ CAREFULLY).
When listing tools, tips, or articles, you MUST check if each item has its OWN dedicated page URL in the knowledge base.

  ✅ PREFERRED — Case A (each item has its own unique page):
    Great for: tools/products that each have a dedicated review page.
    Format:
      1. [Tool Name](https://its-own-page-url.com) — one-line benefit
      2. [Tool Name](https://its-own-page-url.com) — one-line benefit

  Case B — only use if items share ONE source page with NO individual pages:
    1. Item Name — benefit
    2. Item Name — benefit
    📖 **Source:** [Article Title](https://article-url)

IMPORTANT: Scan ALL chunks. If a tool appears in a listicle chunk AND also has its own dedicated chunk with a unique URL → ALWAYS use the dedicated page URL (Case A), not the listicle URL.

• ONLY use URLs from the "Source URL" field in the knowledge chunks.
• NEVER invent or guess URLs.
• Format: `[text](url)` — this renders as a clickable link.

RULE 8 — DEDICATED PAGES ONLY FOR STANDALONE RECOMMENDATIONS.
When recommending tools in a numbered list, ONLY include tools that have their own dedicated page in the knowledge base (i.e., chunks whose Source URL is focused entirely on that one tool, not a roundup/listicle article).

• A tool has a dedicated page if its Source URL is like `/tool-name/` and the content is a review of that specific tool.
• A roundup/listicle article (e.g. "10 Best AI Tools", "Latest AI Tools 2025") may mention tools like GPT-4o, Midjourney, Perplexity etc. — DO NOT list these as standalone numbered recommendations. They don't have dedicated review pages on this website.
• If you can only find 3 tools with dedicated pages for a query, list those 3 and say "We have in-depth reviews on these tools — let me know if you'd like more details on any!"
• NEVER pad the list with tools that only appear as mentions inside roundup articles.

RULE 5 — WEBSITE NAME.
If asked "what is this website?" → look at WEBSITE DOMAIN and answer naturally.

RULE 6 — AGGREGATE.
If asked for 5 items and they're spread across 3 chunks, combine them all into one numbered list.

RULE 7 — SCORING AWARENESS.
Pay attention to the USER BEHAVIOUR data. If intent_level is "High-Intent Lead", be more direct and action-oriented. If the user seems ready to buy/try, end with a clear CTA link.
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
                "Your conversational reply. Use markdown for lists and links. "
                "Format list items as: 1. [Name](URL) — use real URLs from the knowledge base."
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

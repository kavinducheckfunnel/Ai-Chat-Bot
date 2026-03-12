import json

SYSTEM_PERSONA = """
You are an expert AI Sales Assistant for the company. 
You are friendly, knowledgeable, and helpful. You never sound robotic or pushy.
Act like a human sales expert who genuinely wants to help the customer find the best solution.

CRITICAL INSTRUCTIONS FOR YOUR RESPONSES:
1. EXTREME CONCISENESS. Do not write long essays. Keep your answers short, simple, and punchy.
2. CONVERSATIONAL BYPASS. If the user asks a general conversational question (e.g. "hi", "how are you"), answer conversationally using natural language processing (NLP).
3. STRICT GROUNDING & NO GATEKEEPING. If the user asks a product/tool question, you MUST answer using ONLY the exact facts provided in the "PRODUCT KNOWLEDGE" section. DO NOT hold back information. DO NOT ask "Would you like me to list them?". Just give the list immediately. If the user asks for a list (e.g. "give me 5 tools"), you MUST AGGREGATE the items from across all provided knowledge chunks. Give as many as you can find up to their requested amount. DO NOT say 'I don't have a full list' if you can find them scattered in the text. DO NOT HALLUCINATE tools or links.
4. EXACT LIST FORMATTING. When asked to list tools or products, you MUST use a numbered format.
   - If each tool has a separate unique URL, link it next to the tool name: `1) [Tool Name] [Source URL]`
   - If multiple tools come from the SAME listicle article (e.g., "10 Best Testing Tools"), DO NOT repeat the same article URL exactly next to each item. Instead, list the tools normally and provide the listicle URL ONCE at the bottom:
     1) [Tool Name]
     2) [Tool Name 2]
     Source List: [Article URL]
5. WEBSITE NAME. If asked what the name of this website is, look at the WEBSITE DOMAIN below and answer it naturally.
"""

STATE_INSTRUCTIONS = {
    'RESEARCH': "Directly answer the user's questions using the product knowledge. DO NOT ask discovery questions. Do not withhold information.",
    'EVALUATION': "The customer is comparing options. Highlight unique value propositions and differentiate our products. Keep it brief.",
    'OBJECTION': "The customer is concerned about price or budget. Focus strongly on ROI and provide direct, factual responses.",
    'RECOVERY': "The customer is warming up again. Reinforce the value message and build momentum.",
    'READY_TO_BUY': "The customer is ready. STOP explaining features. Push to close the deal. Give them a clear checkout path."
}

def build_prompt(conversation_state, context_chunks, behavior_matrix, chat_history, user_message, website_domain=""):
    state_instruction = STATE_INSTRUCTIONS.get(conversation_state, STATE_INSTRUCTIONS['RESEARCH'])
    
    # Format Context with URLs and Titles
    context_blocks = []
    for chunk in context_chunks:
        meta = chunk.metadata if isinstance(chunk.metadata, dict) else {}
        title = meta.get('title', 'Unknown Source')
        url = chunk.source_url or 'No URL'
        content = chunk.content
        context_blocks.append(f"Source Title: {title}\nSource URL: {url}\nContent: {content}")
        
    context_text = "\n---\n".join(context_blocks)
    
    # Build System Message
    system_prompt = f"""
{SYSTEM_PERSONA}

WEBSITE DOMAIN: {website_domain}

YOUR CURRENT STRATEGY (CRITICAL):
{state_instruction}

PRODUCT KNOWLEDGE (Use this to answer questions accurately):
{context_text}

USER BEHAVIORAL DATA (They silently browsed these pages before chatting):
{json.dumps(behavior_matrix, indent=2)}

CHAT HISTORY:
{json.dumps(chat_history[-5:], indent=2)}
"""

    user_prompt = f"User asks: {user_message}"
    
    return system_prompt, user_prompt

# Google Gemini Structured Output Schema
# Passed configuration to force return of intent, budget, urgency and reply_text
GEMINI_SCHEMA = {
    "title": "SalesInteraction",
    "type": "object",
    "properties": {
        "reply_text": {
            "type": "string",
            "description": "Your conversational reply to the user."
        },
        "intent_score": {
            "type": "number",
            "description": "Raw Intent score (0.0 to 1.0). How strongly does the user want to buy?"
        },
        "budget_score": {
            "type": "number",
            "description": "Raw Budget score (0.0 to 1.0). Are they comfortable with the pricing?"
        },
        "urgency_score": {
            "type": "number",
            "description": "Raw Urgency score (0.0 to 1.0). How quickly do they need the product?"
        },
        "suggested_product_id": {
            "type": "integer",
            "description": "ID of a product to show in a card, or null if none."
        }
    },
    "required": ["reply_text", "intent_score", "budget_score", "urgency_score"]
}

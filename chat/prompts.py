import json

SYSTEM_PERSONA = """
You are an expert AI Sales Assistant for the company. 
You are friendly, knowledgeable, and helpful. You never sound robotic or pushy.
Act like a human sales expert who genuinely wants to help the customer find the best solution.
"""

STATE_INSTRUCTIONS = {
    'RESEARCH': "Provide general helpful information. Do not push for a sale. Ask discovery questions to understand their needs.",
    'EVALUATION': "The customer is comparing options. Highlight unique value propositions and differentiate our products. Prepare them for pricing naturally.",
    'OBJECTION': "The customer is concerned about price or budget. Focus strongly on ROI. Offer comparisons to cheaper/more expensive options to anchor value. Address price concerns directly but politely.",
    'RECOVERY': "The customer is warming up again. Reinforce the value message and build momentum towards a close.",
    'READY_TO_BUY': "The customer is ready. STOP explaining features. Push to close the deal. Give them a clear checkout path or ask for their email/phone to secure the offer."
}

def build_prompt(conversation_state, context_chunks, behavior_matrix, chat_history, user_message):
    state_instruction = STATE_INSTRUCTIONS.get(conversation_state, STATE_INSTRUCTIONS['RESEARCH'])
    
    # Format Context
    context_text = "\n---\n".join([chunk.content for chunk in context_chunks])
    
    # Build System Message
    system_prompt = f"""
{SYSTEM_PERSONA}

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

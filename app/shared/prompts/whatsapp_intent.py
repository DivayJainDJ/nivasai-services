"""
WhatsApp intent detection prompt.
"""

WHATSAPP_INTENT_PROMPT = """Classify the WhatsApp message intent for a civic complaint platform.

Message: {message_text}

Classify the intent and return JSON:
{{
    "intent_type": "<complaint|status_query|help|other>",
    "confidence": <0.0-1.0>,
    "entities": {{}},
    "extracted_data": {{}}
}}

Return ONLY valid JSON.
"""


def get_whatsapp_intent_prompt(message_text: str) -> str:
    """Generate WhatsApp intent prompt."""
    return WHATSAPP_INTENT_PROMPT.format(message_text=message_text)

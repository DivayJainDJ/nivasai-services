"""Multilingual response generation."""

from __future__ import annotations

import os
import time
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

_MODEL = "gemini-2.5-flash"
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy initialization of Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise MultilingualResponderError("GEMINI_API_KEY not configured")
        
        try:
            _client = genai.Client(api_key=api_key)
        except Exception as exc:
            logger.error("gemini_client_init_failed", error=str(exc))
            raise MultilingualResponderError(f"Failed to initialize Gemini client: {exc}") from exc
    
    return _client


class MultilingualResponderError(Exception):
    """Raised when multilingual response generation fails."""


_TRANSLATION_PROMPT_TEMPLATE = """You are a helpful civic assistant translating messages for citizens.

Translate the following message to {target_language}.

Original message:
{message}

Requirements:
- Use simple, citizen-friendly language
- Be warm and helpful
- Maintain the same tone and meaning
- For Hindi: Use Devanagari script
- Keep formatting (line breaks, bullet points)

Return ONLY the translated text, no explanations.
"""


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
def translate_to_hindi(message: str) -> str:
    """Translate message to Hindi."""
    client = _get_client()
    
    prompt = _TRANSLATION_PROMPT_TEMPLATE.format(
        target_language="Hindi (हिंदी)",
        message=message,
    )
    
    started = time.perf_counter()
    
    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.3,
            ),
        )
    except Exception as exc:
        logger.error("gemini_translation_request_failed", error=str(exc))
        raise MultilingualResponderError(f"Translation request failed: {exc}") from exc
    
    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info("gemini_latency", stage="translation", latency_ms=latency_ms)
    
    translated = getattr(response, "text", "")
    if not translated:
        raise MultilingualResponderError("Empty translation response")
    
    return translated.strip()


def generate_bilingual_response(english_message: str, language: str = "en") -> str:
    """Generate bilingual response based on preferred language."""
    if language == "hi":
        try:
            hindi_message = translate_to_hindi(english_message)
            return f"{hindi_message}\n\n---\n\n{english_message}"
        except Exception as exc:
            logger.error("translation_failed", error=str(exc))
            # Fallback to English only
            return english_message
    else:
        return english_message


def generate_greeting(language: str = "en") -> str:
    """Generate greeting message."""
    if language == "hi":
        return (
            "नमस्ते! 🙏\n\n"
            "मैं NivasAI हूं, आपका नागरिक सहायक।\n\n"
            "मैं आपकी मदद कर सकता हूं:\n"
            "• शिकायत दर्ज करें\n"
            "• शिकायत की स्थिति जांचें\n"
            "• किफायती आवास खोजें\n"
            "• नागरिक सेवाओं के बारे में जानकारी\n\n"
            "कृपया बताएं कि मैं आपकी कैसे मदद कर सकता हूं?\n\n"
            "---\n\n"
            "Hello! 🙏\n\n"
            "I'm NivasAI, your civic assistant.\n\n"
            "I can help you:\n"
            "• File complaints\n"
            "• Check complaint status\n"
            "• Find affordable housing\n"
            "• Get civic service information\n\n"
            "How can I help you today?"
        )
    else:
        return (
            "Hello! 🙏\n\n"
            "I'm NivasAI, your civic assistant.\n\n"
            "I can help you:\n"
            "• File complaints\n"
            "• Check complaint status\n"
            "• Find affordable housing\n"
            "• Get civic service information\n\n"
            "How can I help you today?"
        )


def generate_unknown_intent_response(language: str = "en") -> str:
    """Generate response for unknown intent."""
    if language == "hi":
        return (
            "क्षमा करें, मैं समझ नहीं पाया। 🤔\n\n"
            "मैं आपकी मदद कर सकता हूं:\n"
            "• शिकायत दर्ज करें - फोटो और विवरण भेजें\n"
            "• स्थिति जांचें - 'शिकायत 123 की स्थिति' टाइप करें\n"
            "• आवास सहायता - 'आवास सहायता' टाइप करें\n\n"
            "---\n\n"
            "Sorry, I didn't understand that. 🤔\n\n"
            "I can help you:\n"
            "• File complaint - Send photo and description\n"
            "• Check status - Type 'status complaint 123'\n"
            "• Housing help - Type 'housing help'\n\n"
            "What would you like to do?"
        )
    else:
        return (
            "Sorry, I didn't understand that. 🤔\n\n"
            "I can help you:\n"
            "• File complaint - Send photo and description\n"
            "• Check status - Type 'status complaint 123'\n"
            "• Housing help - Type 'housing help'\n\n"
            "What would you like to do?"
        )


def generate_error_response(language: str = "en") -> str:
    """Generate error response."""
    if language == "hi":
        return (
            "क्षमा करें, कुछ गलत हो गया। 😔\n\n"
            "कृपया बाद में पुनः प्रयास करें या अपने स्थानीय नागरिक कार्यालय से संपर्क करें।\n\n"
            "---\n\n"
            "Sorry, something went wrong. 😔\n\n"
            "Please try again later or contact your local civic office."
        )
    else:
        return (
            "Sorry, something went wrong. 😔\n\n"
            "Please try again later or contact your local civic office."
        )

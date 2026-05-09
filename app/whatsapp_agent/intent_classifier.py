"""Intent classification using Gemini."""

from __future__ import annotations

import os
import time
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.whatsapp_agent.schemas import IntentClassification
from app.whatsapp_agent.validator import parse_json_response, validate_intent_classification
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
            raise IntentClassificationError("GEMINI_API_KEY not configured")
        
        try:
            _client = genai.Client(api_key=api_key)
        except Exception as exc:
            logger.error("gemini_client_init_failed", error=str(exc))
            raise IntentClassificationError(f"Failed to initialize Gemini client: {exc}") from exc
    
    return _client


class IntentClassificationError(Exception):
    """Raised when intent classification fails."""


_INTENT_PROMPT_TEMPLATE = """You are a civic assistant AI analyzing citizen messages on WhatsApp.

Classify the user's intent into ONE of these categories:
- complaint_submission: User wants to file a civic complaint (broken road, garbage, water issue, etc.)
- complaint_status: User wants to check status of an existing complaint
- housing_help: User needs help with affordable housing (PMAY, housing schemes, etc.)
- escalation_help: User wants to escalate an issue or speak to higher authority
- ward_information: User wants information about their ward or municipal services
- greeting: User is greeting or starting conversation
- unknown: Intent is unclear or doesn't fit above categories

User message: "{message}"

Detect language:
- "en" for English
- "hi" for Hindi (Devanagari script)

Extract entities:
- For complaint_status: extract complaint ID if mentioned
- For housing_help: extract city, income, family size if mentioned
- For complaint_submission: extract location, issue type if mentioned

Return ONLY valid JSON:
{{
  "intent": "one of the categories above",
  "confidence": 0.0-1.0,
  "language": "en|hi",
  "entities": {{
    "complaintId": "if found",
    "city": "if found",
    "issueType": "if found"
  }}
}}

Examples:
- "Road is broken near school" → complaint_submission
- "Track complaint 123abc" → complaint_status
- "I need PMAY housing" → housing_help
- "Hello" → greeting
- "मुझे घर चाहिए" → housing_help, language: hi
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
def classify_intent(message: str) -> IntentClassification:
    """Classify user intent using Gemini."""
    client = _get_client()
    
    prompt = _INTENT_PROMPT_TEMPLATE.format(message=message)
    
    started = time.perf_counter()
    
    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        logger.error("gemini_intent_request_failed", error=str(exc))
        raise IntentClassificationError(f"Intent classification request failed: {exc}") from exc
    
    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info("gemini_latency", stage="intent_classification", latency_ms=latency_ms)
    
    raw = getattr(response, "text", "")
    if not raw:
        raise IntentClassificationError("Empty Gemini response")
    
    try:
        parsed = parse_json_response(raw)
        intent = validate_intent_classification(parsed)
        
        logger.info(
            "intent_classified",
            intent=intent.intent,
            confidence=intent.confidence,
            language=intent.language,
        )
        
        return intent
    except Exception as exc:
        logger.error("gemini_intent_parse_failed", error=str(exc))
        raise IntentClassificationError(f"Malformed intent response: {exc}") from exc


def create_fallback_intent(message: str) -> IntentClassification:
    """Create fallback intent when Gemini fails."""
    # Simple heuristic-based classification
    message_lower = message.lower()
    
    # Check for greetings
    greetings = ["hello", "hi", "hey", "namaste", "नमस्ते"]
    if any(g in message_lower for g in greetings):
        return IntentClassification(
            intent="greeting",
            confidence=0.7,
            language="hi" if any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in message) else "en",
            entities={},
        )
    
    # Check for status tracking
    status_keywords = ["track", "status", "check", "complaint"]
    if any(k in message_lower for k in status_keywords):
        return IntentClassification(
            intent="complaint_status",
            confidence=0.6,
            language="en",
            entities={},
        )
    
    # Check for housing
    housing_keywords = ["housing", "house", "pmay", "home", "घर"]
    if any(k in message_lower for k in housing_keywords):
        return IntentClassification(
            intent="housing_help",
            confidence=0.6,
            language="hi" if "घर" in message else "en",
            entities={},
        )
    
    # Default to unknown
    return IntentClassification(
        intent="unknown",
        confidence=0.5,
        language="en",
        entities={},
    )

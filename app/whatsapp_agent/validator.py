"""Validation utilities for WhatsApp agent."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.whatsapp_agent.schemas import IntentClassification, WhatsAppMessage


class ValidationException(Exception):
    """Raised when validation fails."""


def validate_whatsapp_message(data: dict[str, Any]) -> WhatsAppMessage:
    """Validate incoming WhatsApp message."""
    try:
        return WhatsAppMessage.model_validate(data)
    except ValidationError as exc:
        raise ValidationException(f"Invalid WhatsApp message: {exc}") from exc


def validate_intent_classification(data: dict[str, Any]) -> IntentClassification:
    """Validate intent classification result."""
    try:
        return IntentClassification.model_validate(data)
    except ValidationError as exc:
        raise ValidationException(f"Invalid intent classification: {exc}") from exc


def parse_json_response(raw: str) -> dict[str, Any]:
    """Parse JSON response from Gemini."""
    text = (raw or "").strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationException(f"Invalid JSON response: {exc}") from exc
    
    if not isinstance(data, dict):
        raise ValidationException("Response must be a JSON object")
    
    return data


def extract_phone_number(whatsapp_from: str) -> str:
    """Extract phone number from WhatsApp 'From' field."""
    # Format: whatsapp:+1234567890
    phone = whatsapp_from.replace("whatsapp:", "").strip()
    return phone


def extract_complaint_id(text: str) -> Optional[str]:
    """Extract complaint ID from user message."""
    # Look for patterns like: 123, #123, complaint 123, ID 123
    patterns = [
        r"#?(\w{20,})",  # Firestore document IDs (20+ chars)
        r"(?:complaint|id|track|status)\s*[:#]?\s*(\w{20,})",
        r"(\w{20,})",  # Fallback: any 20+ char alphanumeric
    ]
    
    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def is_greeting(text: str) -> bool:
    """Check if message is a greeting."""
    greetings = [
        "hello", "hi", "hey", "namaste", "namaskar",
        "good morning", "good afternoon", "good evening",
        "हैलो", "नमस्ते", "नमस्कार",
    ]
    
    text_lower = text.lower().strip()
    return any(greeting in text_lower for greeting in greetings)


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove extra whitespace
    text = " ".join(text.split())
    # Remove special characters but keep basic punctuation
    text = re.sub(r"[^\w\s.,!?।-]", "", text)
    return text.strip()

"""Validation utilities for bot webhook."""

from __future__ import annotations

import re
from typing import Any


class ValidationException(Exception):
    """Raised when validation fails."""


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format."""
    # WhatsApp format: whatsapp:+919999999999
    if phone.startswith("whatsapp:"):
        phone = phone.replace("whatsapp:", "")
    
    # Remove spaces and dashes
    phone = phone.replace(" ", "").replace("-", "")
    
    # Should start with + and have 10-15 digits
    pattern = r"^\+\d{10,15}$"
    return bool(re.match(pattern, phone))


def validate_media_url(url: str) -> bool:
    """Validate media URL."""
    if not url:
        return False
    
    # Should be HTTPS URL
    return url.startswith("https://")


def validate_intent_confidence(confidence: float) -> bool:
    """Validate intent confidence score."""
    return 0.0 <= confidence <= 1.0


def validate_session_integrity(session_data: dict[str, Any]) -> bool:
    """Validate session data integrity."""
    required_fields = ["phone", "preferredLanguage", "conversationHistory"]
    
    for field in required_fields:
        if field not in session_data:
            return False
    
    return True


def sanitize_phone_number(phone: str) -> str:
    """Sanitize phone number."""
    # Remove whatsapp: prefix
    if phone.startswith("whatsapp:"):
        phone = phone.replace("whatsapp:", "")
    
    # Remove spaces and dashes
    phone = phone.replace(" ", "").replace("-", "")
    
    return phone


def validate_complaint_id(complaint_id: str) -> bool:
    """Validate complaint ID format."""
    # Should be alphanumeric with optional dashes
    return bool(re.match(r"^[A-Za-z0-9-]+$", complaint_id))


def validate_twilio_payload(payload: dict[str, Any]) -> bool:
    """Validate Twilio webhook payload."""
    # Must have From field
    if "From" not in payload:
        return False
    
    # Validate phone number
    if not validate_phone_number(payload["From"]):
        return False
    
    return True

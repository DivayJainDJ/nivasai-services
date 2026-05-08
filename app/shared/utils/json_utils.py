"""
JSON utilities for parsing and cleaning Gemini responses.
"""

import json
import re
from typing import Dict, Any


def clean_json_response(response: str) -> str:
    """
    Clean Gemini response by removing markdown wrappers.

    Args:
        response: Raw response from Gemini API

    Returns:
        Clean JSON string

    Raises:
        ValueError: If response is invalid
    """
    if not response or not isinstance(response, str):
        raise ValueError("Response must be a non-empty string")

    # Remove markdown code blocks
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", response)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        raise ValueError("Response is empty after cleaning")

    return cleaned


def extract_json(response: str) -> Dict[str, Any]:
    """Extract and parse JSON from response."""
    cleaned = clean_json_response(response)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")


def is_valid_json(response: str) -> bool:
    """Check if response contains valid JSON."""
    try:
        extract_json(response)
        return True
    except (ValueError, TypeError):
        return False

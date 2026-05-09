"""Parser utilities for Gemini responses."""

from __future__ import annotations

import json
from typing import Any

from app.shared.utils.json_utils import clean_json_response


class GeminiParsingError(Exception):
    """Raised when model output cannot be parsed into JSON."""


def extract_response_text(response_obj: Any) -> str:
    """Extract text from Gemini response object."""
    if isinstance(response_obj, str):
        return response_obj

    text = getattr(response_obj, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    raise GeminiParsingError(f"Unable to extract response text from {type(response_obj)!r}")


def parse_gemini_response_to_dict(raw_response: str) -> dict[str, Any]:
    """Clean and parse Gemini raw output into a dictionary."""
    try:
        cleaned = clean_json_response(raw_response)
        parsed = json.loads(cleaned)
    except (ValueError, json.JSONDecodeError) as exc:
        raise GeminiParsingError(f"Invalid Gemini JSON output: {exc}") from exc

    if not isinstance(parsed, dict):
        raise GeminiParsingError("Gemini output must be a JSON object")

    return parsed

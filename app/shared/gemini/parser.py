"""
Response parser for Gemini API outputs.
"""

from typing import Dict, Any

from app.shared.utils.json_utils import clean_json_response, extract_json


class ParsingError(Exception):
    """Raised when response parsing fails."""

    pass


def parse_gemini_response(response: str) -> Dict[str, Any]:
    """
    Parse Gemini response and extract clean JSON.

    Args:
        response: Raw response from Gemini API

    Returns:
        Parsed JSON as dictionary

    Raises:
        ParsingError: If parsing fails
    """
    if not response or not isinstance(response, str):
        raise ParsingError(f"Invalid response type: {type(response)}")

    try:
        cleaned = clean_json_response(response)
        parsed = extract_json(cleaned)
        return parsed
    except ValueError as e:
        raise ParsingError(f"Failed to parse Gemini response: {str(e)}") from e


def extract_response_text(response_obj: Any) -> str:
    """Extract text content from Gemini response object."""
    try:
        if hasattr(response_obj, "text"):
            return response_obj.text
        elif isinstance(response_obj, str):
            return response_obj
        else:
            raise ParsingError(f"Cannot extract text from type: {type(response_obj)}")
    except AttributeError as e:
        raise ParsingError(f"Missing text attribute: {str(e)}") from e

"""Utilities for extracting clean JSON from model responses."""

from __future__ import annotations

import json
import re


def _strip_code_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _extract_balanced_json(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response")

    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]

    raise ValueError("Incomplete JSON object in model response")


def clean_json_response(response: str) -> str:
    """Return a JSON-only string from a potentially markdown-wrapped response."""
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Response must be a non-empty string")

    cleaned = _strip_code_fence(response).strip()
    if not cleaned:
        raise ValueError("Empty model response after cleanup")

    return _extract_balanced_json(cleaned).strip()


def normalize_json_string(response: str) -> str:
    """Return canonical JSON string after validating parseability."""
    cleaned = clean_json_response(response)
    data = json.loads(cleaned)
    return json.dumps(data, ensure_ascii=False)

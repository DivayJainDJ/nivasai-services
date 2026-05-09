"""Validation utilities for housing matcher."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.housing_matcher.schemas import CitizenInput, GeminiExplanation


class ValidationException(Exception):
    """Raised when validation fails."""


def validate_citizen_input(data: dict[str, Any]) -> CitizenInput:
    """Validate citizen input data."""
    try:
        return CitizenInput.model_validate(data)
    except ValidationError as exc:
        raise ValidationException(f"Invalid citizen input: {exc}") from exc


def validate_gemini_explanation(data: dict[str, Any]) -> GeminiExplanation:
    """Validate Gemini-generated explanation."""
    try:
        return GeminiExplanation.model_validate(data)
    except ValidationError as exc:
        raise ValidationException(f"Invalid Gemini explanation: {exc}") from exc


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


def validate_score_range(score: float, name: str = "score") -> None:
    """Validate score is in valid range."""
    if not 0 <= score <= 100:
        raise ValidationException(f"{name} must be between 0 and 100, got {score}")


def validate_income_eligibility(citizen_income: int, max_income: int) -> bool:
    """Check if citizen income is within eligibility range."""
    return citizen_income <= max_income


def validate_occupancy_eligibility(family_size: int, unit_capacity: int) -> bool:
    """Check if family size fits unit capacity."""
    return family_size <= unit_capacity


def validate_category_eligibility(citizen_category: str, reserved_category: str) -> bool:
    """Check if citizen category matches reserved category."""
    # Normalize categories
    citizen_cat = citizen_category.lower().strip()
    reserved_cat = reserved_category.lower().strip()
    
    # General category can apply to any unit
    if reserved_cat == "general":
        return True
    
    # Exact match required for reserved categories
    return citizen_cat == reserved_cat

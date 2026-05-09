"""Validation and fallback handling for AI output."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.complaint_classifier.department_mapper import map_department
from app.complaint_classifier.schemas import (
    ClassificationResult,
    ComplaintCategory,
)
from app.complaint_classifier.severity_engine import normalize_severity


FALLBACK_RESULT = ClassificationResult(
    category=ComplaintCategory.OTHER,
    severity="low",
    department="Manual Review",
    confidence=0.0,
    summary="Unable to determine civic issue",
    tags=["manual-review"],
    needsHumanReview=True,
)


def parse_model_json(raw_text: str) -> dict[str, Any]:
    """Parse Gemini response text into JSON dict."""
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Model response is not a JSON object")
    return parsed


def _normalize_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["manual-review"]
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        tag = "-".join(item.strip().lower().split())
        if not tag:
            continue
        cleaned.append(tag[:32])
    return cleaned[:6] or ["manual-review"]


def validate_classification_payload(payload: dict[str, Any]) -> ClassificationResult:
    """Validate and normalize model payload to strict schema."""
    category_raw = payload.get("category", ComplaintCategory.OTHER.value)
    if isinstance(category_raw, str) and category_raw in {c.value for c in ComplaintCategory}:
        category = ComplaintCategory(category_raw)
    else:
        category = ComplaintCategory.OTHER

    confidence_raw = payload.get("confidence", 0.0)
    confidence = float(confidence_raw) if isinstance(confidence_raw, (int, float, str)) else 0.0
    confidence = max(0.0, min(1.0, confidence))

    normalized = {
        "category": category,
        "severity": normalize_severity(str(payload.get("severity", "low"))),
        "department": map_department(category),
        "confidence": confidence,
        "summary": str(payload.get("summary", "Unable to determine civic issue")).strip(),
        "tags": _normalize_tags(payload.get("tags", [])),
        "needsHumanReview": bool(payload.get("needsHumanReview", False) or confidence < 0.5),
    }
    try:
        return ClassificationResult.model_validate(normalized)
    except ValidationError:
        return FALLBACK_RESULT

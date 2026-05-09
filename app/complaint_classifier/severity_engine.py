"""Severity normalization and guardrails."""

from __future__ import annotations

from app.complaint_classifier.schemas import ComplaintSeverity


def normalize_severity(value: str) -> ComplaintSeverity:
    """Normalize model severity into allowed enum."""
    normalized = (value or "").strip().lower()
    for candidate in ComplaintSeverity:
        if candidate.value == normalized:
            return candidate
    return ComplaintSeverity.LOW

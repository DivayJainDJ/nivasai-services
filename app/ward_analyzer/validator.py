"""Validation models and guardrails for ward analyzer outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class VisionScorePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roadQuality: int = Field(ge=0, le=100)
    drainageQuality: int = Field(ge=0, le=100)
    sanitationQuality: int = Field(ge=0, le=100)
    greenCoverage: int = Field(ge=0, le=100)
    housingDensity: int = Field(ge=0, le=100)
    floodRisk: int = Field(ge=0, le=100)
    summary: str = Field(min_length=5, max_length=280)
    confidence: float = Field(ge=0.0, le=1.0)


class RemediationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priorityLevel: str = Field(min_length=3, max_length=40)
    keyProblems: list[str] = Field(min_length=1, max_length=10)
    recommendedProjects: list[str] = Field(min_length=1, max_length=12)
    estimatedBudgetINR: int = Field(ge=100000, le=5000000000)
    executionTimeline: str = Field(min_length=3, max_length=80)
    riskAssessment: str = Field(min_length=5, max_length=500)
    phasedPlan: list[str] = Field(min_length=1, max_length=12)
    summary: str = Field(min_length=5, max_length=350)

    @field_validator("keyProblems", "recommendedProjects", "phasedPlan")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if not cleaned:
            raise ValueError("List cannot be empty after cleanup")
        return cleaned


def parse_json_object(raw: str) -> dict[str, Any]:
    import json

    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Gemini response must be a JSON object")
    return data


def validate_vision_payload(data: dict[str, Any]) -> VisionScorePayload:
    try:
        return VisionScorePayload.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid vision payload: {exc}") from exc


def validate_remediation_payload(data: dict[str, Any]) -> RemediationPayload:
    try:
        return RemediationPayload.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid remediation payload: {exc}") from exc

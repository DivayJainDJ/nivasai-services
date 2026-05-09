from __future__ import annotations

import pytest

from app.ward_analyzer.validator import (
    validate_remediation_payload,
    validate_vision_payload,
)


def test_validate_vision_payload_happy_path():
    payload = validate_vision_payload(
        {
            "roadQuality": 60,
            "drainageQuality": 45,
            "sanitationQuality": 70,
            "greenCoverage": 35,
            "housingDensity": 75,
            "floodRisk": 66,
            "summary": "Mixed infrastructure quality with elevated flood vulnerability",
            "confidence": 0.88,
        }
    )
    assert payload.roadQuality == 60


def test_validate_vision_payload_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_vision_payload(
            {
                "roadQuality": 101,
                "drainageQuality": 45,
                "sanitationQuality": 70,
                "greenCoverage": 35,
                "housingDensity": 75,
                "floodRisk": 66,
                "summary": "invalid score",
                "confidence": 0.88,
            }
        )


def test_validate_remediation_payload_happy_path():
    payload = validate_remediation_payload(
        {
            "priorityLevel": "high",
            "keyProblems": ["drainage", "roads"],
            "recommendedProjects": ["Drain rebuild", "Road overlay"],
            "estimatedBudgetINR": 65000000,
            "executionTimeline": "14 months",
            "riskAssessment": "Flood risk persists if drainage remains unaddressed",
            "phasedPlan": ["Design", "Execution", "Monitoring"],
            "summary": "Drainage-first sequence with road rehabilitation.",
        }
    )
    assert payload.estimatedBudgetINR == 65000000

import pytest

from app.complaint_router.service import ComplaintRoutingError, _validate_ai_data


def test_ai_classification_validation_passes():
    payload = {
        "ai": {
            "category": "Garbage",
            "severity": "medium",
            "department": "Sanitation",
            "confidence": 0.81,
        }
    }
    ai = _validate_ai_data(payload)
    assert ai["category"] == "Garbage"


def test_ai_classification_validation_fails_for_missing_fields():
    with pytest.raises(ComplaintRoutingError):
        _validate_ai_data({"ai": {"severity": "high"}})


def test_ai_classification_validation_fails_for_missing_ai_block():
    with pytest.raises(ComplaintRoutingError):
        _validate_ai_data({"description": "no ai block"})

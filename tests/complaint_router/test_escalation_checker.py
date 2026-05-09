from datetime import datetime, timedelta, timezone

from app.complaint_router.escalation_checker import evaluate_escalation


def test_critical_severity_escalates():
    result = evaluate_escalation(
        severity="critical",
        confidence=0.95,
        description="Road collapse reported",
        created_at=datetime.now(timezone.utc),
        status="open",
    )
    assert result.escalated is True
    assert result.escalationLevel == "emergency"
    assert "critical_severity" in result.escalationReasons


def test_high_near_school_escalates_emergency():
    result = evaluate_escalation(
        severity="high",
        confidence=0.9,
        description="Major pothole near school entrance",
        created_at=datetime.now(timezone.utc),
        status="open",
    )
    assert result.emergencyRouting is True
    assert result.escalationLevel == "emergency"
    assert "high_severity_sensitive_zone" in result.escalationReasons


def test_low_confidence_and_sla_breach_escalates():
    result = evaluate_escalation(
        severity="low",
        confidence=0.3,
        description="Unclear issue",
        created_at=datetime.now(timezone.utc) - timedelta(hours=30),
        status="open",
    )
    assert result.escalated is True
    assert result.slaBreached is True
    assert "low_confidence_manual_review" in result.escalationReasons
    assert "sla_breach_24h" in result.escalationReasons

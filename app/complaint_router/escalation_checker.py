"""Escalation and SLA risk detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class EscalationDecision:
    escalated: bool
    escalationLevel: str
    escalationReasons: list[str]
    slaBreached: bool
    emergencyRouting: bool


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return None


def evaluate_escalation(
    *,
    severity: str,
    confidence: float,
    description: str,
    created_at: Any,
    status: str,
) -> EscalationDecision:
    """Evaluate escalation and SLA status from complaint context."""
    reasons: list[str] = []
    normalized_severity = (severity or "").strip().lower()
    normalized_status = (status or "").strip().lower()
    text = (description or "").lower()

    if normalized_severity == "critical":
        reasons.append("critical_severity")

    if normalized_severity == "high" and any(k in text for k in ("school", "hospital")):
        reasons.append("high_severity_sensitive_zone")

    if confidence < 0.5:
        reasons.append("low_confidence_manual_review")

    now = datetime.now(timezone.utc)
    created_dt = _parse_timestamp(created_at)
    sla_breached = False
    if created_dt and normalized_status in {"open", "processing", "assigned"}:
        if now - created_dt > timedelta(hours=24):
            sla_breached = True
            reasons.append("sla_breach_24h")

    emergency = any(reason in reasons for reason in ("critical_severity", "high_severity_sensitive_zone"))
    escalated = bool(reasons)
    if emergency:
        level = "emergency"
    elif "sla_breach_24h" in reasons:
        level = "manager"
    elif "low_confidence_manual_review" in reasons:
        level = "manual-review"
    else:
        level = "none"

    return EscalationDecision(
        escalated=escalated,
        escalationLevel=level,
        escalationReasons=reasons,
        slaBreached=sla_breached,
        emergencyRouting=emergency,
    )

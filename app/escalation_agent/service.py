"""
Escalation agent service.

Handles complaint escalations based on SLA and severity.
"""

from app.shared.logging.logger import get_logger
from app.shared.utils.time_utils import is_sla_breached


logger = get_logger(__name__)


class EscalationAgentService:
    """Manages complaint escalations."""

    @staticmethod
    def check_escalation(
        complaint_id: str, created_at: str, severity: str, status: str
    ) -> dict:
        """Check if complaint needs escalation."""
        sla_hours = {"critical": 4, "high": 24, "medium": 48, "low": 72}.get(
            severity, 72
        )

        breached = is_sla_breached(created_at, sla_hours)

        logger.info(
            "Escalation check",
            complaint_id=complaint_id,
            sla_breached=breached,
            severity=severity,
        )

        return {
            "complaint_id": complaint_id,
            "should_escalate": breached or severity == "critical",
            "sla_hours": sla_hours,
        }


def check_escalation(
    complaint_id: str, created_at: str, severity: str, status: str
) -> dict:
    """Check if escalation is needed."""
    return EscalationAgentService.check_escalation(
        complaint_id, created_at, severity, status
    )

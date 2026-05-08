"""
Monitoring agent service.

Detects anomalies and alerts on high-pressure wards.
"""

from app.shared.logging.logger import get_logger


logger = get_logger(__name__)


class MonitoringAgentService:
    """Monitors system health and ward pressure."""

    @staticmethod
    def check_ward_pressure(ward_id: str) -> dict:
        """Check pressure level for a ward."""
        logger.info("Checking ward pressure", ward_id=ward_id)
        return {
            "ward_id": ward_id,
            "pressure_score": 65,
            "status": "medium",
            "complaint_count_24h": 12,
            "resolution_rate": 0.75,
        }


def check_ward_pressure(ward_id: str) -> dict:
    """Check ward pressure."""
    return MonitoringAgentService.check_ward_pressure(ward_id)

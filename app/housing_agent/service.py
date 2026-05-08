"""
Housing agent service.

Manages fair allocation of housing units.
"""

from app.shared.logging.logger import get_logger


logger = get_logger(__name__)


class HousingAgentService:
    """Manages housing fairness and allocation."""

    @staticmethod
    def allocate_housing(family_id: str, unit_id: str) -> dict:
        """Allocate housing unit to family."""
        logger.info(
            "Allocating housing",
            family_id=family_id,
            unit_id=unit_id,
        )

        return {
            "family_id": family_id,
            "unit_id": unit_id,
            "status": "allocated",
            "allocation_date": "2026-05-08",
        }


def allocate_housing(family_id: str, unit_id: str) -> dict:
    """Allocate housing."""
    return HousingAgentService.allocate_housing(family_id, unit_id)

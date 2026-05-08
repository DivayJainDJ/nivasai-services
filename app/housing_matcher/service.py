"""
Housing matcher service.

Matches families with suitable PMAY housing units.
"""

from app.shared.logging.logger import get_logger


logger = get_logger(__name__)


class HousingMatcherService:
    """Matches families with housing units."""

    @staticmethod
    def match_housing(
        family_id: str, family_size: int, income: float, ward_preference: str
    ) -> dict:
        """
        Find housing matches for a family.

        Args:
            family_id: Family ID
            family_size: Number of family members
            income: Annual income
            ward_preference: Preferred ward

        Returns:
            Matched housing units
        """
        logger.info(
            "Matching housing",
            family_id=family_id,
            family_size=family_size,
            ward=ward_preference,
        )

        # Placeholder matching result
        return {
            "family_id": family_id,
            "matched_units": [
                {
                    "unit_id": "UNIT_001",
                    "ward_id": ward_preference,
                    "bhk_size": "2BHK",
                    "match_score": 92,
                }
            ],
            "total_matches": 1,
        }


def match_housing(
    family_id: str, family_size: int, income: float, ward_preference: str
) -> dict:
    """Convenience function to match housing."""
    return HousingMatcherService.match_housing(
        family_id, family_size, income, ward_preference
    )

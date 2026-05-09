"""Eligibility filtering engine for housing units."""

from __future__ import annotations

from app.housing_matcher.schemas import CitizenInput, HousingUnit
from app.housing_matcher.validator import (
    validate_category_eligibility,
    validate_income_eligibility,
    validate_occupancy_eligibility,
)
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class EligibilityEngine:
    """Filter housing units based on citizen eligibility criteria."""

    def __init__(self, citizen: CitizenInput):
        """Initialize eligibility engine with citizen data."""
        self.citizen = citizen

    def filter_eligible_units(self, units: list[HousingUnit]) -> list[HousingUnit]:
        """Filter units based on all eligibility criteria."""
        eligible_units = []
        
        for unit in units:
            if self._is_eligible(unit):
                eligible_units.append(unit)
        
        logger.info(
            "eligibility_filter_completed",
            total_units=len(units),
            eligible_units=len(eligible_units),
            citizen_income=self.citizen.monthlyIncome,
            family_size=self.citizen.familySize,
            category=self.citizen.category,
        )
        
        return eligible_units

    def _is_eligible(self, unit: HousingUnit) -> bool:
        """Check if citizen is eligible for a specific unit."""
        # Must be available
        if not unit.available:
            return False
        
        # Must be in same city
        if unit.city.lower().strip() != self.citizen.city.lower().strip():
            return False
        
        # Income eligibility
        if not validate_income_eligibility(self.citizen.monthlyIncome, unit.maxIncome):
            return False
        
        # Occupancy eligibility
        if not validate_occupancy_eligibility(self.citizen.familySize, unit.capacity):
            return False
        
        # Category eligibility
        if not validate_category_eligibility(self.citizen.category, unit.reservedCategory):
            return False
        
        return True

    def get_eligibility_reason(self, unit: HousingUnit) -> str:
        """Generate human-readable eligibility reason."""
        reasons = []
        
        if validate_income_eligibility(self.citizen.monthlyIncome, unit.maxIncome):
            reasons.append(
                f"Income ₹{self.citizen.monthlyIncome:,} is within limit of ₹{unit.maxIncome:,}"
            )
        
        if validate_occupancy_eligibility(self.citizen.familySize, unit.capacity):
            reasons.append(
                f"Family size of {self.citizen.familySize} fits capacity of {unit.capacity}"
            )
        
        if validate_category_eligibility(self.citizen.category, unit.reservedCategory):
            if unit.reservedCategory.lower() == "general":
                reasons.append("Unit is open to all categories")
            else:
                reasons.append(f"Category '{self.citizen.category}' matches reserved category")
        
        return "; ".join(reasons) if reasons else "Eligible based on scheme criteria"

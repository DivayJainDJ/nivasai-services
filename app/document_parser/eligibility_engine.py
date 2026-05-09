"""Eligibility determination engine for housing schemes."""

from __future__ import annotations

from app.document_parser.schemas import EligibilityResult
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

# Income thresholds in INR
EWS_THRESHOLD = 300000  # ₹3 lakh per annum
LIG_THRESHOLD = 600000  # ₹6 lakh per annum
MIG_THRESHOLD = 1800000  # ₹18 lakh per annum


class EligibilityEngine:
    """Determine housing eligibility based on income and family data."""

    def determine_eligibility(
        self,
        annual_income: int,
        family_count: int = 1,
    ) -> EligibilityResult:
        """
        Determine eligibility category based on annual income.
        
        Categories:
        - EWS (Economically Weaker Section): Income ≤ ₹3,00,000
        - LIG (Low Income Group): Income ≤ ₹6,00,000
        - MIG (Middle Income Group): Income ≤ ₹18,00,000
        - Not Eligible: Income > ₹18,00,000
        """
        category = self._categorize_income(annual_income)
        is_eligible = category in ["EWS", "LIG", "MIG"]
        eligible_schemes = self._get_eligible_schemes(category, family_count)
        reason = self._generate_reason(category, annual_income)
        
        logger.info(
            "eligibility_determined",
            category=category,
            income=annual_income,
            family_count=family_count,
            eligible=is_eligible,
        )
        
        return EligibilityResult(
            category=category,
            annualIncome=annual_income,
            isEligible=is_eligible,
            eligibleSchemes=eligible_schemes,
            reason=reason,
        )

    def _categorize_income(self, annual_income: int) -> str:
        """Categorize income into EWS/LIG/MIG/Not Eligible."""
        if annual_income <= EWS_THRESHOLD:
            return "EWS"
        elif annual_income <= LIG_THRESHOLD:
            return "LIG"
        elif annual_income <= MIG_THRESHOLD:
            return "MIG"
        else:
            return "Not Eligible"

    def _get_eligible_schemes(self, category: str, family_count: int) -> list[str]:
        """Get list of eligible government schemes."""
        schemes = []
        
        if category == "EWS":
            schemes.extend([
                "PMAY-EWS",
                "State EWS Housing Scheme",
                "Affordable Rental Housing Complex",
            ])
            if family_count >= 4:
                schemes.append("Large Family EWS Subsidy")
        
        elif category == "LIG":
            schemes.extend([
                "PMAY-LIG",
                "State LIG Housing Scheme",
                "Credit Linked Subsidy Scheme",
            ])
        
        elif category == "MIG":
            schemes.extend([
                "PMAY-MIG",
                "Credit Linked Subsidy Scheme",
            ])
        
        return schemes

    def _generate_reason(self, category: str, annual_income: int) -> str:
        """Generate human-readable eligibility reason."""
        if category == "EWS":
            return (
                f"Eligible for EWS category. Annual income ₹{annual_income:,} "
                f"is within EWS threshold of ₹{EWS_THRESHOLD:,}."
            )
        elif category == "LIG":
            return (
                f"Eligible for LIG category. Annual income ₹{annual_income:,} "
                f"is within LIG threshold of ₹{LIG_THRESHOLD:,}."
            )
        elif category == "MIG":
            return (
                f"Eligible for MIG category. Annual income ₹{annual_income:,} "
                f"is within MIG threshold of ₹{MIG_THRESHOLD:,}."
            )
        else:
            return (
                f"Not eligible for housing schemes. Annual income ₹{annual_income:,} "
                f"exceeds MIG threshold of ₹{MIG_THRESHOLD:,}."
            )

    def validate_ews_eligibility(self, annual_income: int) -> bool:
        """Check if income qualifies for EWS."""
        return annual_income <= EWS_THRESHOLD

    def validate_lig_eligibility(self, annual_income: int) -> bool:
        """Check if income qualifies for LIG."""
        return annual_income <= LIG_THRESHOLD

    def validate_pmay_eligibility(
        self,
        annual_income: int,
        family_count: int,
        has_pucca_house: bool = False,
    ) -> bool:
        """
        Validate PMAY (Pradhan Mantri Awas Yojana) eligibility.
        
        Requirements:
        - Income within EWS/LIG/MIG limits
        - No pucca house owned by family
        - Valid family composition
        """
        # Income check
        if annual_income > MIG_THRESHOLD:
            return False
        
        # Pucca house check
        if has_pucca_house:
            return False
        
        # Family count check
        if family_count < 1:
            return False
        
        return True

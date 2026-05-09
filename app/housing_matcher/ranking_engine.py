"""Mathematical ranking engine for housing units."""

from __future__ import annotations

from app.housing_matcher.schemas import CitizenInput, DistanceResult, HousingUnit, RankingScore
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class RankingEngine:
    """Calculate weighted scores for housing units."""

    # Scoring weights (must sum to 100%)
    WEIGHT_AFFORDABILITY = 0.35  # 35%
    WEIGHT_DISTANCE = 0.25  # 25%
    WEIGHT_OCCUPANCY = 0.20  # 20%
    WEIGHT_URGENCY = 0.10  # 10%
    WEIGHT_ACCESSIBILITY = 0.10  # 10%

    def __init__(self, citizen: CitizenInput):
        """Initialize ranking engine with citizen data."""
        self.citizen = citizen

    def calculate_score(
        self,
        unit: HousingUnit,
        distance_result: DistanceResult,
    ) -> RankingScore:
        """Calculate comprehensive ranking score for a unit."""
        affordability_score = self._calculate_affordability_score(unit)
        distance_score = self._calculate_distance_score(distance_result.distanceKm)
        occupancy_score = self._calculate_occupancy_score(unit)
        urgency_score = self._calculate_urgency_score()
        accessibility_score = distance_result.accessibilityScore
        
        # Calculate weighted total score
        total_score = (
            affordability_score * self.WEIGHT_AFFORDABILITY
            + distance_score * self.WEIGHT_DISTANCE
            + occupancy_score * self.WEIGHT_OCCUPANCY
            + urgency_score * self.WEIGHT_URGENCY
            + accessibility_score * self.WEIGHT_ACCESSIBILITY
        )
        
        return RankingScore(
            affordabilityScore=round(affordability_score, 2),
            distanceScore=round(distance_score, 2),
            occupancyScore=round(occupancy_score, 2),
            urgencyScore=round(urgency_score, 2),
            accessibilityScore=round(accessibility_score, 2),
            totalScore=round(total_score, 2),
        )

    def _calculate_affordability_score(self, unit: HousingUnit) -> float:
        """
        Calculate affordability score based on price vs income.
        
        Better affordability = higher score
        """
        monthly_income = self.citizen.monthlyIncome
        unit_price = unit.priceINR
        
        # Calculate price-to-income ratio (in months)
        if monthly_income == 0:
            return 0.0
        
        price_to_income_months = unit_price / monthly_income
        
        # Scoring based on affordability
        # < 24 months: Excellent (100)
        # 24-36 months: Very Good (80)
        # 36-48 months: Good (60)
        # 48-60 months: Moderate (40)
        # > 60 months: Poor (20)
        
        if price_to_income_months <= 24:
            return 100.0
        elif price_to_income_months <= 36:
            return 80.0
        elif price_to_income_months <= 48:
            return 60.0
        elif price_to_income_months <= 60:
            return 40.0
        else:
            return 20.0

    def _calculate_distance_score(self, distance_km: float) -> float:
        """
        Calculate distance score (inverse of distance).
        
        Closer = higher score
        """
        # Same scoring as accessibility
        if distance_km <= 5:
            return 100.0
        elif distance_km <= 10:
            return 80.0
        elif distance_km <= 20:
            return 60.0
        elif distance_km <= 30:
            return 40.0
        else:
            return 20.0

    def _calculate_occupancy_score(self, unit: HousingUnit) -> float:
        """
        Calculate occupancy fit score.
        
        Perfect fit = highest score
        Underutilized = lower score
        """
        family_size = self.citizen.familySize
        unit_capacity = unit.capacity
        
        if family_size > unit_capacity:
            # Should not happen (filtered in eligibility)
            return 0.0
        
        # Calculate utilization ratio
        utilization = family_size / unit_capacity
        
        # Scoring based on utilization
        # 80-100% utilization: Excellent (100)
        # 60-80% utilization: Good (80)
        # 40-60% utilization: Moderate (60)
        # 20-40% utilization: Low (40)
        # < 20% utilization: Poor (20)
        
        if utilization >= 0.8:
            return 100.0
        elif utilization >= 0.6:
            return 80.0
        elif utilization >= 0.4:
            return 60.0
        elif utilization >= 0.2:
            return 40.0
        else:
            return 20.0

    def _calculate_urgency_score(self) -> float:
        """
        Calculate urgency score based on citizen's urgency level.
        
        Higher urgency = higher score
        """
        urgency_map = {
            "high": 100.0,
            "medium": 60.0,
            "low": 30.0,
        }
        
        return urgency_map.get(self.citizen.urgencyLevel, 60.0)

    def rank_units(
        self,
        units: list[HousingUnit],
        distance_results: dict[str, DistanceResult],
    ) -> list[tuple[HousingUnit, RankingScore, DistanceResult]]:
        """
        Rank all units and return sorted list.
        
        Returns list of (unit, score, distance) tuples sorted by score descending.
        """
        ranked = []
        
        for unit in units:
            distance_result = distance_results.get(unit.unitId)
            if not distance_result:
                logger.warning("missing_distance_result", unit_id=unit.unitId)
                continue
            
            score = self.calculate_score(unit, distance_result)
            ranked.append((unit, score, distance_result))
        
        # Sort by total score descending
        ranked.sort(key=lambda x: x[1].totalScore, reverse=True)
        
        logger.info(
            "ranking_completed",
            total_units=len(ranked),
            top_score=ranked[0][1].totalScore if ranked else 0,
        )
        
        return ranked

    def get_top_matches(
        self,
        units: list[HousingUnit],
        distance_results: dict[str, DistanceResult],
        top_n: int = 3,
    ) -> list[tuple[HousingUnit, RankingScore, DistanceResult]]:
        """Get top N ranked units."""
        ranked = self.rank_units(units, distance_results)
        return ranked[:top_n]

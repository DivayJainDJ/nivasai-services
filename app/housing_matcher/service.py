"""Main housing matcher service orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone

from app.housing_matcher.distance_scorer import DistanceScorer
from app.housing_matcher.eligibility_engine import EligibilityEngine
from app.housing_matcher.explanation_generator import ExplanationGenerator
from app.housing_matcher.ranking_engine import RankingEngine
from app.housing_matcher.schemas import CitizenInput, HousingMatch, HousingMatchResponse, HousingUnit
from app.housing_matcher.validator import validate_citizen_input
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class HousingMatcherError(Exception):
    """Raised when housing matching fails."""


def get_mock_housing_units(city: str) -> list[HousingUnit]:
    """
    Get mock housing units for testing.
    
    In production, this would fetch from Firestore.
    """
    # Normalize city name
    city_lower = city.lower().strip()
    
    # Mock housing units database
    all_units = [
        HousingUnit(
            unitId="unit_101",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=30000,
            capacity=4,
            priceINR=850000,
            latitude=12.9716,
            longitude=77.5946,
            reservedCategory="general",
            available=True,
            address="Whitefield, Bangalore",
            amenities=["Water supply", "Electricity", "Parking"],
        ),
        HousingUnit(
            unitId="unit_102",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=25000,
            capacity=3,
            priceINR=650000,
            latitude=12.9352,
            longitude=77.6245,
            reservedCategory="general",
            available=True,
            address="Electronic City, Bangalore",
            amenities=["Water supply", "Electricity", "Security"],
        ),
        HousingUnit(
            unitId="unit_103",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=35000,
            capacity=5,
            priceINR=1200000,
            latitude=13.0358,
            longitude=77.5970,
            reservedCategory="sc",
            available=True,
            address="Yelahanka, Bangalore",
            amenities=["Water supply", "Electricity", "Parking", "Playground"],
        ),
        HousingUnit(
            unitId="unit_104",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=28000,
            capacity=4,
            priceINR=750000,
            latitude=12.9141,
            longitude=77.6411,
            reservedCategory="general",
            available=True,
            address="HSR Layout, Bangalore",
            amenities=["Water supply", "Electricity", "Parking"],
        ),
        HousingUnit(
            unitId="unit_105",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=32000,
            capacity=3,
            priceINR=900000,
            latitude=12.9698,
            longitude=77.7500,
            reservedCategory="general",
            available=True,
            address="Marathahalli, Bangalore",
            amenities=["Water supply", "Electricity", "Security", "Parking"],
        ),
        HousingUnit(
            unitId="unit_106",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=20000,
            capacity=2,
            priceINR=450000,
            latitude=12.9279,
            longitude=77.6271,
            reservedCategory="general",
            available=True,
            address="Koramangala, Bangalore",
            amenities=["Water supply", "Electricity"],
        ),
        HousingUnit(
            unitId="unit_107",
            scheme="PMAY",
            city="Mumbai",
            maxIncome=40000,
            capacity=4,
            priceINR=1500000,
            latitude=19.0760,
            longitude=72.8777,
            reservedCategory="general",
            available=True,
            address="Andheri, Mumbai",
            amenities=["Water supply", "Electricity", "Parking", "Security"],
        ),
        HousingUnit(
            unitId="unit_108",
            scheme="PMAY",
            city="Delhi",
            maxIncome=35000,
            capacity=4,
            priceINR=1100000,
            latitude=28.7041,
            longitude=77.1025,
            reservedCategory="general",
            available=True,
            address="Rohini, Delhi",
            amenities=["Water supply", "Electricity", "Parking"],
        ),
    ]
    
    # Filter by city
    city_units = [u for u in all_units if u.city.lower() == city_lower]
    
    logger.info("mock_units_fetched", city=city, total_units=len(city_units))
    
    return city_units


def match_housing(citizen_data: dict) -> HousingMatchResponse:
    """
    Main housing matching pipeline.
    
    Steps:
    1. Validate citizen input
    2. Fetch housing units
    3. Filter eligible units
    4. Calculate distances
    5. Rank units
    6. Generate explanations for top 3
    7. Build final response
    """
    logger.info("housing_match_started", citizen_name=citizen_data.get("citizenName"))
    
    try:
        # Step 1: Validate input
        citizen = validate_citizen_input(citizen_data)
        
        # Step 2: Fetch housing units (mock data for now)
        all_units = get_mock_housing_units(citizen.city)
        
        if not all_units:
            logger.warning("no_units_found", city=citizen.city)
            return _create_no_match_response(citizen, all_units)
        
        # Step 3: Filter eligible units
        eligibility_engine = EligibilityEngine(citizen)
        eligible_units = eligibility_engine.filter_eligible_units(all_units)
        
        if not eligible_units:
            logger.warning("no_eligible_units", city=citizen.city)
            return _create_no_match_response(citizen, all_units)
        
        # Step 4: Calculate distances
        distance_scorer = DistanceScorer()
        distance_results = distance_scorer.calculate_distances_batch(
            citizen.latitude,
            citizen.longitude,
            eligible_units,
        )
        
        # Step 5: Rank units and get top 3
        ranking_engine = RankingEngine(citizen)
        top_matches = ranking_engine.get_top_matches(eligible_units, distance_results, top_n=3)
        
        if not top_matches:
            logger.warning("no_ranked_matches")
            return _create_no_match_response(citizen, all_units)
        
        # Step 6: Generate explanations for top matches
        explanation_generator = ExplanationGenerator(citizen)
        
        matches_for_explanation = [
            (
                unit,
                score,
                distance_result.distanceKm,
                eligibility_engine.get_eligibility_reason(unit),
            )
            for unit, score, distance_result in top_matches
        ]
        
        explanations = explanation_generator.generate_explanations_batch(matches_for_explanation)
        
        # Step 7: Build final response
        housing_matches = []
        
        for unit, score, distance_result in top_matches:
            explanation = explanations.get(unit.unitId)
            if not explanation:
                logger.warning("missing_explanation", unit_id=unit.unitId)
                continue
            
            housing_match = HousingMatch(
                unitId=unit.unitId,
                scheme=unit.scheme,
                city=unit.city,
                priceINR=unit.priceINR,
                address=unit.address or f"{unit.city} Housing Unit",
                score=score.totalScore,
                distanceKm=distance_result.distanceKm,
                estimatedTravelMinutes=distance_result.durationMinutes,
                affordabilityScore=score.affordabilityScore,
                englishExplanation=explanation.englishExplanation,
                hindiExplanation=explanation.hindiExplanation,
                eligibilityReason=explanation.eligibilityReason,
                documentChecklist=explanation.documentChecklist,
                nextSteps=explanation.nextSteps,
            )
            
            housing_matches.append(housing_match)
        
        response = HousingMatchResponse(
            success=True,
            citizen={
                "name": citizen.citizenName,
                "monthlyIncome": citizen.monthlyIncome,
                "familySize": citizen.familySize,
                "city": citizen.city,
                "category": citizen.category,
                "urgencyLevel": citizen.urgencyLevel,
            },
            matches=housing_matches,
            totalUnitsEvaluated=len(all_units),
            totalEligibleUnits=len(eligible_units),
            generatedAt=datetime.now(timezone.utc).isoformat(),
        )
        
        logger.info(
            "response_completed",
            citizen_name=citizen.citizenName,
            matches_found=len(housing_matches),
        )
        
        return response
    
    except Exception as exc:
        logger.error("housing_match_failed", error=str(exc))
        raise HousingMatcherError(f"Housing matching failed: {exc}") from exc


def _create_no_match_response(citizen: CitizenInput, all_units: list[HousingUnit]) -> HousingMatchResponse:
    """Create response when no matches are found."""
    return HousingMatchResponse(
        success=True,
        citizen={
            "name": citizen.citizenName,
            "monthlyIncome": citizen.monthlyIncome,
            "familySize": citizen.familySize,
            "city": citizen.city,
            "category": citizen.category,
            "urgencyLevel": citizen.urgencyLevel,
        },
        matches=[],
        totalUnitsEvaluated=len(all_units),
        totalEligibleUnits=0,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )

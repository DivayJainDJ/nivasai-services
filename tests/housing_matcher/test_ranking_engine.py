"""Tests for ranking engine."""

from __future__ import annotations

import pytest

from app.housing_matcher.ranking_engine import RankingEngine
from app.housing_matcher.schemas import CitizenInput, DistanceResult, HousingUnit


@pytest.fixture
def citizen():
    """Create test citizen."""
    return CitizenInput(
        citizenName="Test Citizen",
        monthlyIncome=25000,
        familySize=4,
        city="Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        category="general",
        preferredLanguage="en",
        urgencyLevel="high",
    )


@pytest.fixture
def housing_unit():
    """Create test housing unit."""
    return HousingUnit(
        unitId="unit_101",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=30000,
        capacity=4,
        priceINR=600000,  # 24 months of income
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="general",
        available=True,
    )


@pytest.fixture
def distance_result():
    """Create test distance result."""
    return DistanceResult(
        distanceKm=5.0,
        durationMinutes=15,
        accessibilityScore=100.0,
    )


def test_calculate_score(citizen, housing_unit, distance_result):
    """Test score calculation."""
    engine = RankingEngine(citizen)
    
    score = engine.calculate_score(housing_unit, distance_result)
    
    assert 0 <= score.totalScore <= 100
    assert 0 <= score.affordabilityScore <= 100
    assert 0 <= score.distanceScore <= 100
    assert 0 <= score.occupancyScore <= 100
    assert 0 <= score.urgencyScore <= 100
    assert 0 <= score.accessibilityScore <= 100


def test_affordability_score_excellent(citizen):
    """Test affordability score for excellent affordability."""
    engine = RankingEngine(citizen)
    
    # 24 months of income = excellent
    unit = HousingUnit(
        unitId="unit_101",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=30000,
        capacity=4,
        priceINR=600000,  # 24 months
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="general",
        available=True,
    )
    
    score = engine._calculate_affordability_score(unit)
    assert score == 100.0


def test_affordability_score_poor(citizen):
    """Test affordability score for poor affordability."""
    engine = RankingEngine(citizen)
    
    # 72 months of income = poor
    unit = HousingUnit(
        unitId="unit_102",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=30000,
        capacity=4,
        priceINR=1800000,  # 72 months
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="general",
        available=True,
    )
    
    score = engine._calculate_affordability_score(unit)
    assert score == 20.0


def test_distance_score_close(citizen):
    """Test distance score for close distance."""
    engine = RankingEngine(citizen)
    
    score = engine._calculate_distance_score(3.0)  # 3 km
    assert score == 100.0


def test_distance_score_far(citizen):
    """Test distance score for far distance."""
    engine = RankingEngine(citizen)
    
    score = engine._calculate_distance_score(35.0)  # 35 km
    assert score == 20.0


def test_occupancy_score_perfect_fit(citizen):
    """Test occupancy score for perfect fit."""
    engine = RankingEngine(citizen)
    
    # Family of 4, capacity 4 = 100% utilization
    unit = HousingUnit(
        unitId="unit_103",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=30000,
        capacity=4,
        priceINR=850000,
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="general",
        available=True,
    )
    
    score = engine._calculate_occupancy_score(unit)
    assert score == 100.0


def test_occupancy_score_underutilized(citizen):
    """Test occupancy score for underutilized unit."""
    engine = RankingEngine(citizen)
    
    # Family of 4, capacity 10 = 40% utilization
    unit = HousingUnit(
        unitId="unit_104",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=30000,
        capacity=10,
        priceINR=850000,
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="general",
        available=True,
    )
    
    score = engine._calculate_occupancy_score(unit)
    assert score == 60.0


def test_urgency_score_high():
    """Test urgency score for high urgency."""
    citizen = CitizenInput(
        citizenName="Test Citizen",
        monthlyIncome=25000,
        familySize=4,
        city="Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        category="general",
        preferredLanguage="en",
        urgencyLevel="high",
    )
    
    engine = RankingEngine(citizen)
    score = engine._calculate_urgency_score()
    assert score == 100.0


def test_urgency_score_low():
    """Test urgency score for low urgency."""
    citizen = CitizenInput(
        citizenName="Test Citizen",
        monthlyIncome=25000,
        familySize=4,
        city="Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        category="general",
        preferredLanguage="en",
        urgencyLevel="low",
    )
    
    engine = RankingEngine(citizen)
    score = engine._calculate_urgency_score()
    assert score == 30.0


def test_rank_units(citizen):
    """Test ranking multiple units."""
    engine = RankingEngine(citizen)
    
    units = [
        HousingUnit(
            unitId="unit_101",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=30000,
            capacity=4,
            priceINR=600000,
            latitude=12.9716,
            longitude=77.5946,
            reservedCategory="general",
            available=True,
        ),
        HousingUnit(
            unitId="unit_102",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=30000,
            capacity=4,
            priceINR=1200000,
            latitude=12.9716,
            longitude=77.5946,
            reservedCategory="general",
            available=True,
        ),
    ]
    
    distance_results = {
        "unit_101": DistanceResult(distanceKm=5.0, durationMinutes=15, accessibilityScore=100.0),
        "unit_102": DistanceResult(distanceKm=25.0, durationMinutes=45, accessibilityScore=40.0),
    }
    
    ranked = engine.rank_units(units, distance_results)
    
    assert len(ranked) == 2
    # First unit should rank higher (better affordability and distance)
    assert ranked[0][0].unitId == "unit_101"
    assert ranked[0][1].totalScore > ranked[1][1].totalScore


def test_get_top_matches(citizen):
    """Test getting top N matches."""
    engine = RankingEngine(citizen)
    
    units = [
        HousingUnit(
            unitId=f"unit_{i}",
            scheme="PMAY",
            city="Bangalore",
            maxIncome=30000,
            capacity=4,
            priceINR=600000 + (i * 100000),
            latitude=12.9716,
            longitude=77.5946,
            reservedCategory="general",
            available=True,
        )
        for i in range(5)
    ]
    
    distance_results = {
        f"unit_{i}": DistanceResult(distanceKm=5.0 + i, durationMinutes=15 + i * 5, accessibilityScore=100.0 - i * 10)
        for i in range(5)
    }
    
    top_matches = engine.get_top_matches(units, distance_results, top_n=3)
    
    assert len(top_matches) == 3
    # Scores should be in descending order
    assert top_matches[0][1].totalScore >= top_matches[1][1].totalScore
    assert top_matches[1][1].totalScore >= top_matches[2][1].totalScore

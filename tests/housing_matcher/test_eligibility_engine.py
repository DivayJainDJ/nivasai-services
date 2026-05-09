"""Tests for eligibility engine."""

from __future__ import annotations

import pytest

from app.housing_matcher.eligibility_engine import EligibilityEngine
from app.housing_matcher.schemas import CitizenInput, HousingUnit


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
        urgencyLevel="medium",
    )


@pytest.fixture
def eligible_unit():
    """Create eligible housing unit."""
    return HousingUnit(
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
    )


@pytest.fixture
def ineligible_income_unit():
    """Create unit with income too low."""
    return HousingUnit(
        unitId="unit_102",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=20000,  # Too low
        capacity=4,
        priceINR=650000,
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="general",
        available=True,
    )


@pytest.fixture
def ineligible_capacity_unit():
    """Create unit with capacity too small."""
    return HousingUnit(
        unitId="unit_103",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=30000,
        capacity=2,  # Too small
        priceINR=650000,
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="general",
        available=True,
    )


def test_filter_eligible_units(citizen, eligible_unit, ineligible_income_unit):
    """Test filtering eligible units."""
    engine = EligibilityEngine(citizen)
    units = [eligible_unit, ineligible_income_unit]
    
    eligible = engine.filter_eligible_units(units)
    
    assert len(eligible) == 1
    assert eligible[0].unitId == "unit_101"


def test_income_eligibility(citizen, eligible_unit, ineligible_income_unit):
    """Test income eligibility check."""
    engine = EligibilityEngine(citizen)
    
    assert engine._is_eligible(eligible_unit) is True
    assert engine._is_eligible(ineligible_income_unit) is False


def test_capacity_eligibility(citizen, eligible_unit, ineligible_capacity_unit):
    """Test capacity eligibility check."""
    engine = EligibilityEngine(citizen)
    
    assert engine._is_eligible(eligible_unit) is True
    assert engine._is_eligible(ineligible_capacity_unit) is False


def test_city_filter(citizen):
    """Test city filtering."""
    engine = EligibilityEngine(citizen)
    
    wrong_city_unit = HousingUnit(
        unitId="unit_104",
        scheme="PMAY",
        city="Mumbai",  # Wrong city
        maxIncome=30000,
        capacity=4,
        priceINR=850000,
        latitude=19.0760,
        longitude=72.8777,
        reservedCategory="general",
        available=True,
    )
    
    assert engine._is_eligible(wrong_city_unit) is False


def test_availability_filter(citizen, eligible_unit):
    """Test availability filtering."""
    engine = EligibilityEngine(citizen)
    
    unavailable_unit = HousingUnit(
        unitId="unit_105",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=30000,
        capacity=4,
        priceINR=850000,
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="general",
        available=False,  # Not available
    )
    
    assert engine._is_eligible(unavailable_unit) is False


def test_category_eligibility_general():
    """Test category eligibility for general category."""
    citizen = CitizenInput(
        citizenName="Test Citizen",
        monthlyIncome=25000,
        familySize=4,
        city="Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        category="general",
        preferredLanguage="en",
        urgencyLevel="medium",
    )
    
    engine = EligibilityEngine(citizen)
    
    general_unit = HousingUnit(
        unitId="unit_106",
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
    
    assert engine._is_eligible(general_unit) is True


def test_category_eligibility_reserved():
    """Test category eligibility for reserved category."""
    citizen = CitizenInput(
        citizenName="Test Citizen",
        monthlyIncome=25000,
        familySize=4,
        city="Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        category="sc",
        preferredLanguage="en",
        urgencyLevel="medium",
    )
    
    engine = EligibilityEngine(citizen)
    
    reserved_unit = HousingUnit(
        unitId="unit_107",
        scheme="PMAY",
        city="Bangalore",
        maxIncome=30000,
        capacity=4,
        priceINR=850000,
        latitude=12.9716,
        longitude=77.5946,
        reservedCategory="sc",
        available=True,
    )
    
    assert engine._is_eligible(reserved_unit) is True


def test_get_eligibility_reason(citizen, eligible_unit):
    """Test eligibility reason generation."""
    engine = EligibilityEngine(citizen)
    
    reason = engine.get_eligibility_reason(eligible_unit)
    
    assert "Income" in reason
    assert "Family size" in reason
    assert "25,000" in reason or "25000" in reason

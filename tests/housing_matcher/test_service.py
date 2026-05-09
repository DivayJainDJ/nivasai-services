"""Tests for housing matcher service."""

from __future__ import annotations

import pytest

from app.housing_matcher.service import match_housing
from app.housing_matcher.validator import ValidationException


def test_match_housing_success():
    """Test successful housing match."""
    citizen_data = {
        "citizenName": "Rajesh Kumar",
        "monthlyIncome": 25000,
        "familySize": 4,
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "category": "general",
        "preferredLanguage": "en",
        "urgencyLevel": "high",
    }
    
    response = match_housing(citizen_data)
    
    assert response.success is True
    assert response.citizen["name"] == "Rajesh Kumar"
    assert len(response.matches) > 0
    assert len(response.matches) <= 3  # Top 3 matches
    
    # Check first match structure
    first_match = response.matches[0]
    assert first_match.unitId
    assert first_match.scheme
    assert 0 <= first_match.score <= 100
    assert first_match.distanceKm >= 0
    assert first_match.englishExplanation
    assert first_match.hindiExplanation
    assert len(first_match.documentChecklist) > 0
    assert len(first_match.nextSteps) > 0


def test_match_housing_no_eligible_units():
    """Test when no eligible units are found."""
    citizen_data = {
        "citizenName": "Test Citizen",
        "monthlyIncome": 100000,  # Too high for any unit
        "familySize": 4,
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "category": "general",
        "preferredLanguage": "en",
        "urgencyLevel": "medium",
    }
    
    response = match_housing(citizen_data)
    
    assert response.success is True
    assert len(response.matches) == 0
    assert response.totalEligibleUnits == 0


def test_match_housing_wrong_city():
    """Test when citizen is in a city with no units."""
    citizen_data = {
        "citizenName": "Test Citizen",
        "monthlyIncome": 25000,
        "familySize": 4,
        "city": "Chennai",  # No units in Chennai
        "latitude": 13.0827,
        "longitude": 80.2707,
        "category": "general",
        "preferredLanguage": "en",
        "urgencyLevel": "medium",
    }
    
    response = match_housing(citizen_data)
    
    assert response.success is True
    assert len(response.matches) == 0


def test_match_housing_invalid_input():
    """Test with invalid input data."""
    citizen_data = {
        "citizenName": "Test Citizen",
        "monthlyIncome": -1000,  # Invalid negative income
        "familySize": 4,
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "category": "general",
        "preferredLanguage": "en",
        "urgencyLevel": "medium",
    }
    
    with pytest.raises(ValidationException):
        match_housing(citizen_data)


def test_match_housing_bilingual_response():
    """Test that response includes both English and Hindi explanations."""
    citizen_data = {
        "citizenName": "Priya Sharma",
        "monthlyIncome": 20000,
        "familySize": 3,
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "category": "general",
        "preferredLanguage": "hi",
        "urgencyLevel": "medium",
    }
    
    response = match_housing(citizen_data)
    
    if response.matches:
        first_match = response.matches[0]
        assert first_match.englishExplanation
        assert first_match.hindiExplanation
        # Check that Hindi explanation contains Devanagari characters
        assert any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in first_match.hindiExplanation)


def test_match_housing_document_checklist():
    """Test that document checklist is generated."""
    citizen_data = {
        "citizenName": "Test Citizen",
        "monthlyIncome": 25000,
        "familySize": 4,
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "category": "general",
        "preferredLanguage": "en",
        "urgencyLevel": "medium",
    }
    
    response = match_housing(citizen_data)
    
    if response.matches:
        first_match = response.matches[0]
        assert len(first_match.documentChecklist) >= 3
        # Check for common documents
        checklist_str = " ".join(first_match.documentChecklist).lower()
        assert "aadhaar" in checklist_str or "aadhar" in checklist_str


def test_match_housing_next_steps():
    """Test that next steps are generated."""
    citizen_data = {
        "citizenName": "Test Citizen",
        "monthlyIncome": 25000,
        "familySize": 4,
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "category": "general",
        "preferredLanguage": "en",
        "urgencyLevel": "medium",
    }
    
    response = match_housing(citizen_data)
    
    if response.matches:
        first_match = response.matches[0]
        assert len(first_match.nextSteps) >= 3
        # Check that steps are actionable
        steps_str = " ".join(first_match.nextSteps).lower()
        assert "visit" in steps_str or "submit" in steps_str or "apply" in steps_str


def test_match_housing_score_ordering():
    """Test that matches are ordered by score."""
    citizen_data = {
        "citizenName": "Test Citizen",
        "monthlyIncome": 25000,
        "familySize": 4,
        "city": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "category": "general",
        "preferredLanguage": "en",
        "urgencyLevel": "medium",
    }
    
    response = match_housing(citizen_data)
    
    if len(response.matches) > 1:
        # Scores should be in descending order
        for i in range(len(response.matches) - 1):
            assert response.matches[i].score >= response.matches[i + 1].score


def test_match_housing_reserved_category():
    """Test matching with reserved category."""
    citizen_data = {
        "citizenName": "Test Citizen",
        "monthlyIncome": 30000,
        "familySize": 5,
        "city": "Bangalore",
        "latitude": 13.0358,
        "longitude": 77.5970,
        "category": "sc",
        "preferredLanguage": "en",
        "urgencyLevel": "high",
    }
    
    response = match_housing(citizen_data)
    
    # Should find at least the reserved unit
    assert response.success is True
    if response.matches:
        # Check that at least one match is for the reserved category
        assert any(match.unitId == "unit_103" for match in response.matches)

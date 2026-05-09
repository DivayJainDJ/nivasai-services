"""Pydantic schemas for housing matcher."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CitizenInput(BaseModel):
    """Input schema for citizen housing match request."""

    citizenName: str = Field(min_length=2, max_length=100)
    monthlyIncome: int = Field(ge=0, le=500000)
    familySize: int = Field(ge=1, le=20)
    city: str = Field(min_length=2, max_length=50)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category: str = Field(min_length=2, max_length=30)
    preferredLanguage: Literal["en", "hi"] = "en"
    urgencyLevel: Literal["low", "medium", "high"] = "medium"

    @field_validator("citizenName", "city", "category")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        return value.strip()


class HousingUnit(BaseModel):
    """Housing unit data model."""

    unitId: str
    scheme: str
    city: str
    maxIncome: int
    capacity: int
    priceINR: int
    latitude: float
    longitude: float
    reservedCategory: str
    available: bool
    address: str = ""
    amenities: list[str] = Field(default_factory=list)


class DistanceResult(BaseModel):
    """Distance calculation result."""

    distanceKm: float = Field(ge=0)
    durationMinutes: int = Field(ge=0)
    accessibilityScore: float = Field(ge=0, le=100)


class RankingScore(BaseModel):
    """Ranking score breakdown."""

    affordabilityScore: float = Field(ge=0, le=100)
    distanceScore: float = Field(ge=0, le=100)
    occupancyScore: float = Field(ge=0, le=100)
    urgencyScore: float = Field(ge=0, le=100)
    accessibilityScore: float = Field(ge=0, le=100)
    totalScore: float = Field(ge=0, le=100)


class GeminiExplanation(BaseModel):
    """Gemini-generated explanation for a housing match."""

    englishExplanation: str = Field(min_length=10, max_length=1000)
    hindiExplanation: str = Field(min_length=10, max_length=1000)
    eligibilityReason: str = Field(min_length=10, max_length=500)
    documentChecklist: list[str] = Field(min_length=1, max_length=15)
    nextSteps: list[str] = Field(min_length=1, max_length=10)

    @field_validator("documentChecklist", "nextSteps")
    @classmethod
    def validate_string_list(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if not cleaned:
            raise ValueError("List cannot be empty after cleanup")
        return cleaned


class HousingMatch(BaseModel):
    """Complete housing match result."""

    unitId: str
    scheme: str
    city: str
    priceINR: int
    address: str
    score: float = Field(ge=0, le=100)
    distanceKm: float = Field(ge=0)
    estimatedTravelMinutes: int = Field(ge=0)
    affordabilityScore: float = Field(ge=0, le=100)
    englishExplanation: str
    hindiExplanation: str
    eligibilityReason: str
    documentChecklist: list[str]
    nextSteps: list[str]


class HousingMatchResponse(BaseModel):
    """Final API response for housing match."""

    success: bool
    citizen: dict
    matches: list[HousingMatch]
    totalUnitsEvaluated: int
    totalEligibleUnits: int
    generatedAt: str

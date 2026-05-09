"""Schemas for complaint classification and intake."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComplaintCategory(str, Enum):
    ROAD_DAMAGE = "Road Damage"
    GARBAGE = "Garbage"
    DRAINAGE = "Drainage"
    WATER_LEAKAGE = "Water Leakage"
    STREETLIGHT_ISSUE = "Streetlight Issue"
    ELECTRICAL_HAZARD = "Electrical Hazard"
    TRAFFIC_ISSUE = "Traffic Issue"
    ILLEGAL_DUMPING = "Illegal Dumping"
    PUBLIC_SAFETY = "Public Safety"
    SEWAGE = "Sewage"
    FLOODING = "Flooding"
    OTHER = "Other"


class ComplaintSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClassificationResult(BaseModel):
    """AI classification payload stored in Firestore."""

    model_config = ConfigDict(extra="forbid")

    category: ComplaintCategory
    severity: ComplaintSeverity
    department: str = Field(min_length=3, max_length=64)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=5, max_length=180)
    tags: list[str] = Field(min_length=1, max_length=6)
    needsHumanReview: bool

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if len(normalized.split()) > 20:
            raise ValueError("summary must be 20 words or fewer")
        return normalized

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags: list[str]) -> list[str]:
        cleaned: list[str] = []
        for tag in tags:
            normalized = "-".join(tag.strip().lower().split())
            if not normalized:
                continue
            cleaned.append(normalized[:32])
        if not cleaned:
            raise ValueError("at least one valid tag required")
        return cleaned[:6]


class CreateComplaintResponse(BaseModel):
    success: Literal[True]
    complaintId: str
    status: Literal["processing"]


class ComplaintDocument(BaseModel):
    """Firestore complaint document required fields."""

    description: str
    imageUrl: str
    latitude: float
    longitude: float
    address: str
    userId: str
    status: str
    aiProcessed: bool

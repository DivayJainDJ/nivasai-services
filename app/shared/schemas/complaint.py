"""Strict schema for complaint-classifier output."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ComplaintCategory(str, Enum):
    WATER = "water"
    WASTE = "waste"
    ROADS = "roads"
    ELECTRICITY = "electricity"
    STREET_LIGHTING = "street_lighting"
    DRAINAGE = "drainage"
    PUBLIC_HEALTH = "public_health"
    POLLUTION = "pollution"
    OTHER = "other"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Department(str, Enum):
    BWSSB = "BWSSB"
    BBMP = "BBMP"
    BESCOM = "BESCOM"
    HEALTH = "HEALTH"
    KSPCB = "KSPCB"
    OTHER = "OTHER"


class ComplaintSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: ComplaintCategory
    severity: SeverityLevel
    summary: str = Field(min_length=5, max_length=280)
    department: Department
    confidence: float = Field(ge=0.0, le=1.0)

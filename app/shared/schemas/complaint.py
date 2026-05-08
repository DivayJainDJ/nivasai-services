"""
Complaint schema with strict validation.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ComplaintCategory(str, Enum):
    """Valid complaint categories."""

    WATER_SANITATION = "water_sanitation"
    WASTE_MANAGEMENT = "waste_management"
    ROAD_INFRASTRUCTURE = "road_infrastructure"
    ELECTRICITY = "electricity"
    STREET_LIGHTING = "street_lighting"
    PARK_MAINTENANCE = "park_maintenance"
    DRAINAGE = "drainage"
    PUBLIC_HEALTH = "public_health"
    POLLUTION = "pollution"
    OTHER = "other"


class SeverityLevel(str, Enum):
    """Severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Department(str, Enum):
    """Responsible departments."""

    WATER_BOARD = "water_board"
    SANITATION = "sanitation"
    ROADS = "roads"
    ELECTRICITY = "electricity"
    PARKS = "parks"
    DRAINAGE = "drainage"
    HEALTH = "health"
    POLLUTION = "pollution"
    OTHER = "other"


class ComplaintSchema(BaseModel):
    """Complaint classification schema."""

    category: ComplaintCategory = Field(..., description="Category of complaint")
    severity: SeverityLevel = Field(..., description="Severity level")
    summary: str = Field(
        ..., min_length=5, max_length=500, description="Brief summary"
    )
    department: Department = Field(..., description="Responsible department")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score"
    )

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
    }

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is valid probability."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence must be 0.0-1.0, got {v}")
        return v

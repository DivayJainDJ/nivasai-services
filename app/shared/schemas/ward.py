"""
Ward analysis schema.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any


class WardInfrastructureScore(BaseModel):
    """Infrastructure quality score for a ward."""

    roads: float = Field(..., ge=0, le=100)
    drainage: float = Field(..., ge=0, le=100)
    street_lighting: float = Field(..., ge=0, le=100)
    water_supply: float = Field(..., ge=0, le=100)
    sanitation: float = Field(..., ge=0, le=100)
    overall: float = Field(..., ge=0, le=100)


class WardAnalysisSchema(BaseModel):
    """Ward satellite imagery analysis result."""

    ward_id: str
    infrastructure_scores: WardInfrastructureScore
    pressure_level: str  # low, medium, high, critical
    recommendations: List[str] = Field(max_length=10)
    analysis_date: str

"""
Housing allocation schema.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class HousingUnit(BaseModel):
    """Housing unit details."""

    unit_id: str
    ward_id: str
    location: Dict[str, float]  # {latitude, longitude}
    bhk_size: str  # 1BHK, 2BHK, etc.
    availability_status: str  # available, occupied, reserved
    proximity_score: float = Field(ge=0, le=100)


class HousingMatchSchema(BaseModel):
    """Housing match result for a family."""

    family_id: str
    matched_units: List[HousingUnit]
    total_matches: int
    matching_criteria: Dict[str, Any]
    match_date: str

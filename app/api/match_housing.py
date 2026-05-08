"""
Housing matching API endpoint.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.housing_matcher.service import match_housing

router = APIRouter()


class HousingMatchRequest(BaseModel):
    """Housing match request."""

    family_id: str
    family_size: int
    income: float
    ward_preference: str


@router.post("/matchHousing")
async def match_housing_endpoint(request: HousingMatchRequest):
    """Find housing matches for a family."""
    try:
        result = match_housing(
            request.family_id,
            request.family_size,
            request.income,
            request.ward_preference,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

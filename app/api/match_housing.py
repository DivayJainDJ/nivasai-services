"""Housing matching API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.housing_matcher.service import HousingMatcherError, match_housing
from app.housing_matcher.validator import ValidationException

router = APIRouter()


class HousingMatchRequest(BaseModel):
    """Request schema for housing match endpoint."""

    citizenName: str
    monthlyIncome: int
    familySize: int
    city: str
    latitude: float
    longitude: float
    category: str
    preferredLanguage: str = "en"
    urgencyLevel: str = "medium"


@router.post("/match-housing")
async def match_housing_endpoint(request: HousingMatchRequest):
    """
    Match citizen with best affordable housing units.
    
    This endpoint:
    1. Validates citizen eligibility
    2. Filters housing units by income, family size, and category
    3. Calculates distances using Google Distance Matrix API
    4. Ranks units using weighted scoring algorithm
    5. Generates bilingual explanations using Gemini AI
    6. Returns top 3 matches with complete details
    """
    try:
        # Convert request to dict for service
        citizen_data = request.model_dump()
        
        # Call housing matcher service
        response = match_housing(citizen_data)
        
        return response.model_dump()
    
    except ValidationException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    
    except HousingMatcherError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Housing matching failed: {exc}",
        ) from exc

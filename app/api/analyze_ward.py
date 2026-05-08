"""
Ward analysis API endpoint.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ward_analyzer.service import analyze_ward

router = APIRouter()


class WardAnalysisRequest(BaseModel):
    """Ward analysis request."""

    ward_id: str
    latitude: float
    longitude: float


@router.post("/analyzeWard")
async def analyze_ward_endpoint(request: WardAnalysisRequest):
    """Analyze ward infrastructure using satellite imagery."""
    try:
        result = analyze_ward(request.ward_id, request.latitude, request.longitude)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

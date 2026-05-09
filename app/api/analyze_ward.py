"""Ward analysis API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.ward_analyzer.service import WardAnalysisError, analyze_ward

router = APIRouter()


@router.post("/analyze-ward")
async def analyze_ward_endpoint(
    satelliteImage: UploadFile = File(...),
    wardName: str = Form(...),
    population: int = Form(...),
    city: str = Form(...),
    state: str = Form(...),
):
    """Analyze a municipal ward using satellite imagery and metadata."""
    try:
        if population <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="population must be positive")

        image_bytes = await satelliteImage.read()
        return analyze_ward(
            satellite_image_bytes=image_bytes,
            satellite_content_type=satelliteImage.content_type or "",
            ward_name=wardName.strip(),
            population=population,
            city=city.strip(),
            state=state.strip(),
        )
    except HTTPException:
        raise
    except WardAnalysisError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ward analysis failed: {exc}",
        ) from exc

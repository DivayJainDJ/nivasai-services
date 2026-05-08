"""
API endpoints for ward analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.dependencies import get_current_user, get_services
from app.shared.schemas.ward import WardAnalysisRequest, WardAnalysisResponse
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class WardAnalysisRequest(BaseModel):
    """Request model for ward analysis"""
    ward_id: str = Field(..., description="Ward ID")
    ward_name: str = Field(..., description="Ward name")
    coordinates: dict = Field(..., description="Ward coordinates {lat, lng}")
    analysis_type: str = Field(default="comprehensive", description="Analysis type")
    include_recommendations: bool = Field(default=True, description="Include recommendations")


class WardAnalysisResponse(BaseModel):
    """Response model for ward analysis"""
    success: bool
    analysis_id: Optional[str] = None
    message: str
    data: Optional[dict] = None


@router.post("/analyze", response_model=dict)
async def analyze_ward(
    request: WardAnalysisRequest,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Analyze ward infrastructure
    
    Args:
        request: Ward analysis request
        user: Current user
        services: Service dependencies
        
    Returns:
        Ward analysis results
    """
    try:
        logger.info(
            "Starting ward analysis",
            ward_id=request.ward_id,
            user_id=user.get('id'),
            analysis_type=request.analysis_type
        )
        
        # Validate user permissions
        if user.get('role') not in ['admin', 'officer', 'analyst']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Perform analysis
        analysis = await services.ward_analyzer.analyze_ward_infrastructure(
            ward_id=request.ward_id,
            ward_name=request.ward_name,
            coordinates=request.coordinates,
            analysis_type=request.analysis_type
        )
        
        logger.info(
            "Ward analysis completed",
            ward_id=request.ward_id,
            overall_score=analysis.scores.overall_score
        )
        
        return {
            "success": True,
            "analysis_id": analysis.ward_id,
            "message": "Ward analysis completed successfully",
            "data": analysis.dict()
        }
        
    except Exception as e:
        logger.error(
            "Ward analysis failed",
            ward_id=request.ward_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ward_id}", response_model=dict)
async def get_ward_analysis(
    ward_id: str,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Get existing ward analysis
    
    Args:
        ward_id: Ward ID
        user: Current user
        services: Service dependencies
        
    Returns:
        Ward analysis data
    """
    try:
        logger.info(
            "Fetching ward analysis",
            ward_id=ward_id,
            user_id=user.get('id')
        )
        
        # Get analysis summary
        summary = await services.ward_analyzer.get_ward_analysis_summary(ward_id)
        
        if 'error' in summary:
            raise HTTPException(status_code=404, detail="Ward analysis not found")
        
        return {
            "success": True,
            "data": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch ward analysis",
            ward_id=ward_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=dict)
async def batch_analyze_wards(
    ward_requests: List[WardAnalysisRequest],
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Analyze multiple wards in batch
    
    Args:
        ward_requests: List of ward analysis requests
        user: Current user
        services: Service dependencies
        
    Returns:
        Batch analysis results
    """
    try:
        logger.info(
            "Starting batch ward analysis",
            ward_count=len(ward_requests),
            user_id=user.get('id')
        )
        
        # Validate user permissions
        if user.get('role') not in ['admin', 'analyst']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Prepare batch requests
        batch_requests = []
        for request in ward_requests:
            batch_requests.append({
                'ward_id': request.ward_id,
                'ward_name': request.ward_name,
                'coordinates': request.coordinates,
                'analysis_type': request.analysis_type
            })
        
        # Perform batch analysis
        analyses = await services.ward_analyzer.batch_analyze_wards(batch_requests)
        
        logger.info(
            "Batch ward analysis completed",
            total_requested=len(ward_requests),
            successful=len(analyses)
        )
        
        return {
            "success": True,
            "total_requested": len(ward_requests),
            "successful": len(analyses),
            "analyses": [analysis.dict() for analysis in analyses]
        }
        
    except Exception as e:
        logger.error(
            "Batch ward analysis failed",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison", response_model=dict)
async def compare_wards(
    ward_ids: List[str] = Query(..., description="List of ward IDs to compare"),
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Compare multiple wards
    
    Args:
        ward_ids: List of ward IDs
        user: Current user
        services: Service dependencies
        
    Returns:
        Ward comparison data
    """
    try:
        logger.info(
            "Comparing wards",
            ward_ids=ward_ids,
            user_id=user.get('id')
        )
        
        # Get analysis for each ward
        comparisons = []
        for ward_id in ward_ids:
            summary = await services.ward_analyzer.get_ward_analysis_summary(ward_id)
            if 'error' not in summary:
                comparisons.append({
                    'ward_id': ward_id,
                    'overall_score': summary['summary']['overall_score'],
                    'priority_level': summary['summary']['priority_level'],
                    'top_priority': summary['summary']['top_priority'],
                    'project_count': summary['summary']['project_count']
                })
        
        # Sort by score
        comparisons.sort(key=lambda x: x['overall_score'], reverse=True)
        
        return {
            "success": True,
            "comparisons": comparisons,
            "ranking": [comp['ward_id'] for comp in comparisons]
        }
        
    except Exception as e:
        logger.error(
            "Ward comparison failed",
            ward_ids=ward_ids,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranking", response_model=dict)
async def get_ward_ranking(
    limit: int = Query(default=10, ge=1, le=100, description="Number of wards to return"),
    sort_by: str = Query(default="overall_score", description="Sort by field"),
    order: str = Query(default="desc", description="Sort order (asc/desc)"),
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Get ward ranking
    
    Args:
        limit: Number of wards to return
        sort_by: Sort field
        order: Sort order
        user: Current user
        services: Service dependencies
        
    Returns:
        Ranked wards
    """
    try:
        logger.info(
            "Getting ward ranking",
            limit=limit,
            sort_by=sort_by,
            order=order,
            user_id=user.get('id')
        )
        
        # This would query Firestore for all ward analyses and sort them
        # For now, return mock data
        rankings = [
            {
                "rank": 1,
                "ward_id": "ward_001",
                "ward_name": "Central Ward",
                "overall_score": 8.5,
                "priority_level": "low"
            },
            {
                "rank": 2,
                "ward_id": "ward_002", 
                "ward_name": "North Ward",
                "overall_score": 7.2,
                "priority_level": "medium"
            }
        ][:limit]
        
        return {
            "success": True,
            "rankings": rankings
        }
        
    except Exception as e:
        logger.error(
            "Ward ranking failed",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{ward_id}", response_model=dict)
async def get_ward_trends(
    ward_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days for trend analysis"),
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Get ward trends over time
    
    Args:
        ward_id: Ward ID
        days: Number of days for analysis
        user: Current user
        services: Service dependencies
        
    Returns:
        Ward trend data
    """
    try:
        logger.info(
            "Getting ward trends",
            ward_id=ward_id,
            days=days,
            user_id=user.get('id')
        )
        
        # This would analyze historical data for the ward
        # For now, return mock trend data
        trends = {
            "ward_id": ward_id,
            "period_days": days,
            "infrastructure_score_trend": [
                {"date": "2024-01-01", "score": 7.2},
                {"date": "2024-01-02", "score": 7.3},
                {"date": "2024-01-03", "score": 7.1}
            ],
            "complaint_trend": [
                {"date": "2024-01-01", "count": 5},
                {"date": "2024-01-02", "count": 3},
                {"date": "2024-01-03", "count": 7}
            ]
        }
        
        return {
            "success": True,
            "trends": trends
        }
        
    except Exception as e:
        logger.error(
            "Ward trends failed",
            ward_id=ward_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

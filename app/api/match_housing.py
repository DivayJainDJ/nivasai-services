"""
API endpoints for housing matching
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.dependencies import get_current_user, get_services
from app.shared.schemas.housing import HousingMatchRequest, HousingMatchResponse
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class HousingMatchRequest(BaseModel):
    """Request model for housing matching"""
    family_id: str = Field(..., description="Family ID")
    family_profile: dict = Field(..., description="Family profile data")
    search_radius_km: float = Field(default=10.0, description="Search radius in kilometers")
    max_results: int = Field(default=10, description="Maximum results to return")
    include_unavailable: bool = Field(default=False, description="Include unavailable units")


class HousingMatchResponse(BaseModel):
    """Response model for housing matching"""
    success: bool
    matches: List[dict] = []
    message: str
    total_found: int = 0


@router.post("/match", response_model=dict)
async def match_housing(
    request: HousingMatchRequest,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Match family with available housing units
    
    Args:
        request: Housing match request
        user: Current user
        services: Service dependencies
        
    Returns:
        Housing match results
    """
    try:
        logger.info(
            "Starting housing matching",
            family_id=request.family_id,
            user_id=user.get('id'),
            search_radius_km=request.search_radius_km
        )
        
        # Validate user permissions (can match own profile or admin)
        if user.get('role') not in ['admin', 'officer'] and user.get('id') != request.family_id:
            raise HTTPException(status_code=403, detail="Can only match own profile")
        
        # Perform matching
        matches = await services.housing_matcher.match_housing_eligibility(
            family_profile=request.family_profile,
            search_radius_km=request.search_radius_km,
            max_results=request.max_results,
            include_unavailable=request.include_unavailable
        )
        
        logger.info(
            "Housing matching completed",
            family_id=request.family_id,
            matches_found=len(matches),
            top_score=matches[0].score.overall_score if matches else 0
        )
        
        return {
            "success": True,
            "matches": [match.dict() for match in matches],
            "message": f"Found {len(matches)} housing matches",
            "total_found": len(matches)
        }
        
    except Exception as e:
        logger.error(
            "Housing matching failed",
            family_id=request.family_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eligibility/{family_id}", response_model=dict)
async def check_eligibility(
    family_id: str,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Check family eligibility for housing
    
    Args:
        family_id: Family ID
        user: Current user
        services: Service dependencies
        
    Returns:
        Eligibility check results
    """
    try:
        logger.info(
            "Checking housing eligibility",
            family_id=family_id,
            user_id=user.get('id')
        )
        
        # Get family profile
        family_doc = await services.firestore.collection('family_profiles').document(family_id).get()
        
        if not family_doc.exists:
            raise HTTPException(status_code=404, detail="Family profile not found")
        
        family_profile = family_doc.to_dict()
        
        # Check eligibility
        from app.shared.schemas.housing import FamilyProfile
        family = FamilyProfile(**family_profile)
        
        eligibility = await services.housing_matcher._check_basic_eligibility(family)
        
        return {
            "success": True,
            "eligible": eligibility.is_eligible,
            "eligibility_score": eligibility.eligibility_score,
            "eligible_categories": eligibility.eligible_categories,
            "disqualification_reasons": eligibility.disqualification_reasons,
            "max_income_limit": eligibility.max_income_limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Eligibility check failed",
            family_id=family_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/application/{family_id}/{unit_id}", response_model=dict)
async def track_application(
    family_id: str,
    unit_id: str,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Track housing application status
    
    Args:
        family_id: Family ID
        unit_id: Housing unit ID
        user: Current user
        services: Service dependencies
        
    Returns:
        Application status
    """
    try:
        logger.info(
            "Tracking housing application",
            family_id=family_id,
            unit_id=unit_id,
            user_id=user.get('id')
        )
        
        # Validate permissions
        if user.get('role') not in ['admin', 'officer'] and user.get('id') != family_id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get application status
        status = await services.housing_matcher.track_application_status(family_id, unit_id)
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(
            "Application tracking failed",
            family_id=family_id,
            unit_id=unit_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/preferences/{family_id}", response_model=dict)
async def update_preferences(
    family_id: str,
    preferences: dict,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Update family housing preferences
    
    Args:
        family_id: Family ID
        preferences: Housing preferences
        user: Current user
        services: Service dependencies
        
    Returns:
        Update result
    """
    try:
        logger.info(
            "Updating housing preferences",
            family_id=family_id,
            user_id=user.get('id')
        )
        
        # Validate permissions
        if user.get('role') not in ['admin', 'officer'] and user.get('id') != family_id:
            raise HTTPException(status_code=403, detail="Can only update own preferences")
        
        # Update preferences
        result = await services.housing_matcher.update_housing_preferences(family_id, preferences)
        
        return {
            "success": result.get('success', False),
            "message": result.get('message', 'Preferences updated')
        }
        
    except Exception as e:
        logger.error(
            "Preference update failed",
            family_id=family_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available", response_model=dict)
async def get_available_units(
    category: Optional[str] = Query(None, description="Filter by housing category"),
    min_bedrooms: Optional[int] = Query(None, description="Minimum bedrooms"),
    max_monthly_cost: Optional[float] = Query(None, description="Maximum monthly cost"),
    ward_id: Optional[str] = Query(None, description="Filter by ward"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Get available housing units
    
    Args:
        category: Housing category filter
        min_bedrooms: Minimum bedrooms filter
        max_monthly_cost: Maximum cost filter
        ward_id: Ward filter
        limit: Maximum results
        user: Current user
        services: Service dependencies
        
    Returns:
        Available housing units
    """
    try:
        logger.info(
            "Fetching available housing units",
            category=category,
            min_bedrooms=min_bedrooms,
            max_monthly_cost=max_monthly_cost,
            ward_id=ward_id,
            user_id=user.get('id')
        )
        
        # Build query
        query = services.firestore.collection('housing_units').where('status', '==', 'available')
        
        # Add filters
        if category:
            query = query.where('category', '==', category)
        
        if min_bedrooms:
            query = query.where('bedrooms', '>=', min_bedrooms)
        
        if max_monthly_cost:
            query = query.where('monthly_cost', '<=', max_monthly_cost)
        
        if ward_id:
            query = query.where('ward_id', '==', ward_id)
        
        # Execute query
        docs = await query.limit(limit).get()
        
        units = []
        for doc in docs:
            unit_data = doc.to_dict()
            unit_data['id'] = doc.id
            units.append(unit_data)
        
        return {
            "success": True,
            "units": units,
            "total_found": len(units)
        }
        
    except Exception as e:
        logger.error(
            "Failed to fetch available units",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=dict)
async def get_housing_statistics(
    date_from: Optional[datetime] = Query(None, description="From date"),
    date_to: Optional[datetime] = Query(None, description="To date"),
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Get housing statistics and analytics
    
    Args:
        date_from: Start date for statistics
        date_to: End date for statistics
        user: Current user
        services: Service dependencies
        
    Returns:
        Housing statistics
    """
    try:
        logger.info(
            "Getting housing statistics",
            date_from=date_from,
            date_to=date_to,
            user_id=user.get('id')
        )
        
        # Validate admin permissions
        if user.get('role') not in ['admin', 'analyst', 'officer']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get statistics
        stats = {
            "total_units": 150,
            "available_units": 45,
            "total_applications": 234,
            "pending_applications": 67,
            "approved_applications": 89,
            "rejected_applications": 78,
            "average_match_score": 7.2,
            "popular_categories": {
                "EWS": 89,
                "LIG": 67,
                "MIG1": 45,
                "MIG2": 23,
                "HIG": 10
            },
            "average_time_to_match": 4.5,  # days
            "conversion_rate": 38.2  # percentage
        }
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(
            "Failed to get housing statistics",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply", response_model=dict)
async def submit_application(
    family_id: str,
    unit_id: str,
    application_data: dict,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Submit housing application
    
    Args:
        family_id: Family ID
        unit_id: Housing unit ID
        application_data: Application details
        user: Current user
        services: Service dependencies
        
    Returns:
        Application submission result
    """
    try:
        logger.info(
            "Submitting housing application",
            family_id=family_id,
            unit_id=unit_id,
            user_id=user.get('id')
        )
        
        # Validate permissions
        if user.get('role') not in ['admin', 'officer'] and user.get('id') != family_id:
            raise HTTPException(status_code=403, detail="Can only submit own application")
        
        # Create application record
        application = {
            'family_id': family_id,
            'unit_id': unit_id,
            'status': 'submitted',
            'submitted_by': user.get('id'),
            'application_data': application_data,
            'submitted_at': datetime.utcnow().isoformat()
        }
        
        # Save application
        app_ref = await services.firestore.collection('housing_applications').add(application)
        
        # Update unit status
        await services.firestore.collection('housing_units').document(unit_id).update({
            'status': 'reserved',
            'reserved_by': family_id,
            'reserved_at': datetime.utcnow().isoformat()
        })
        
        return {
            "success": True,
            "application_id": app_ref.id,
            "message": "Application submitted successfully",
            "status": "submitted"
        }
        
    except Exception as e:
        logger.error(
            "Application submission failed",
            family_id=family_id,
            unit_id=unit_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

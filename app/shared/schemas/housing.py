"""
Pydantic schemas for housing-related data structures
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum


class HousingCategory(str, Enum):
    """Housing categories"""
    EWS = "EWS"  # Economically Weaker Section
    LIG = "LIG"  # Lower Income Group
    MIG1 = "MIG1"  # Middle Income Group 1
    MIG2 = "MIG2"  # Middle Income Group 2
    HIG = "HIG"  # Higher Income Group


class HousingType(str, Enum):
    """Housing types"""
    APARTMENT = "apartment"
    INDEPENDENT_HOUSE = "independent_house"
    DUPLEX = "duplex"
    STUDIO = "studio"
    VILLA = "villa"


class ApplicationStatus(str, Enum):
    """Application status"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    APPROVED = "approved"
    REJECTED = "rejected"
    ALLOTTED = "allotted"
    WITHDRAWN = "withdrawn"


class FamilyProfile(BaseModel):
    """Family profile for housing eligibility"""
    family_id: str = Field(..., description="Family ID")
    primary_applicant_name: str = Field(..., min_length=3, max_length=100)
    primary_applicant_age: int = Field(..., ge=18, le=70, description="Primary applicant age")
    family_size: int = Field(..., ge=1, le=8, description="Number of family members")
    category: HousingCategory = Field(..., description="Housing category")
    annual_income: float = Field(..., ge=0, description="Annual income in rupees")
    current_location: Dict[str, float] = Field(..., description="Current location {lat, lng}")
    has_local_residence: bool = Field(..., description="Has local residence proof")
    owns_property: bool = Field(..., description="Owns any property")
    preferred_localities: List[str] = Field(default_factory=list, description="Preferred localities")
    preferred_floor_range: Optional[Tuple[int, int]] = Field(None, description="Preferred floor range (min, max)")
    required_amenities: List[str] = Field(default_factory=list, description="Required amenities")
    max_monthly_cost: Optional[float] = Field(None, description="Maximum monthly cost willing to pay")
    
    # Special categories
    is_senior_citizen: bool = Field(default=False, description="Is senior citizen")
    is_disabled: bool = Field(default=False, description="Has disability")
    is_widow: bool = Field(default=False, description="Is widow")
    is_single_woman: bool = Field(default=False, description="Is single woman")
    is_minority: bool = Field(default=False, description="Belongs to minority community")
    
    special_categories: List[str] = Field(default_factory=list, description="Special categories")
    
    @validator('special_categories', pre=True, always=True)
    def set_special_categories(cls, v, values):
        """Set special categories based on boolean flags"""
        if not v:
            v = []
        
        categories = {
            'senior_citizen': values.get('is_senior_citizen', False),
            'disabled': values.get('is_disabled', False),
            'widow': values.get('is_widow', False),
            'single_woman': values.get('is_single_woman', False),
            'minority': values.get('is_minority', False)
        }
        
        for category, is_present in categories.items():
            if is_present and category not in v:
                v.append(category)
        
        return v
    
    class Config:
        from_attributes = True


class HousingUnit(BaseModel):
    """Housing unit details"""
    id: str = Field(..., description="Unit ID")
    type: HousingType = Field(..., description="Housing type")
    category: HousingCategory = Field(..., description="Housing category")
    location: Dict[str, float] = Field(..., description="Unit location {lat, lng}")
    locality: str = Field(..., description="Locality/area name")
    ward_id: str = Field(..., description="Ward ID")
    
    # Unit details
    bedrooms: int = Field(..., ge=1, le=4, description="Number of bedrooms")
    bathrooms: int = Field(..., ge=1, le=3, description="Number of bathrooms")
    area_sqft: float = Field(..., ge=200, description="Area in square feet")
    floor_number: int = Field(..., ge=0, description="Floor number")
    total_floors: int = Field(..., ge=1, description="Total floors in building")
    
    # Financial details
    monthly_cost: float = Field(..., ge=0, description="Monthly cost in rupees")
    maintenance_cost: Optional[float] = Field(None, description="Monthly maintenance cost")
    deposit_amount: Optional[float] = Field(None, description="Deposit amount")
    
    # Eligibility
    eligible_categories: List[HousingCategory] = Field(..., description="Eligible categories")
    max_income: float = Field(..., description="Maximum income eligibility")
    min_bedrooms: int = Field(..., description="Minimum bedrooms required")
    max_bedrooms: int = Field(..., description="Maximum bedrooms allowed")
    special_categories: Dict[str, bool] = Field(default_factory=dict, description="Special category preferences")
    
    # Amenities and features
    amenities: List[str] = Field(default_factory=list, description="Available amenities")
    features: List[str] = Field(default_factory=list, description="Special features")
    
    # Status and availability
    status: str = Field(..., description="Unit status")
    available_from: Optional[datetime] = Field(None, description="Available from date")
    reserved_by: Optional[str] = Field(None, description="Reserved by family ID")
    
    # Distance
    distance_km: float = Field(..., description="Distance from search location")
    
    class Config:
        from_attributes = True


class EligibilityResult(BaseModel):
    """Eligibility check result"""
    is_eligible: bool = Field(..., description="Whether family is eligible")
    eligibility_score: float = Field(..., ge=0.0, le=100.0, description="Eligibility score (0-100)")
    disqualification_reasons: List[str] = Field(default_factory=list, description="Reasons for disqualification")
    eligible_categories: List[HousingCategory] = Field(default_factory=list, description="Eligible categories")
    max_income_limit: float = Field(..., description="Maximum income limit for category")
    
    class Config:
        from_attributes = True


class MatchScore(BaseModel):
    """Housing match score components"""
    eligibility_score: float = Field(..., ge=0.0, le=100.0, description="Eligibility score (0-100)")
    distance_score: float = Field(..., ge=0.0, le=100.0, description="Distance score (0-100)")
    size_fit_score: float = Field(..., ge=0.0, le=100.0, description="Size fit score (0-100)")
    preference_score: float = Field(..., ge=0.0, le=100.0, description="Preference score (0-100)")
    availability_score: float = Field(..., ge=0.0, le=100.0, description="Availability score (0-100)")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall match score (0-100)")
    
    class Config:
        from_attributes = True


class HousingMatch(BaseModel):
    """Housing match result"""
    family_id: str = Field(..., description="Family ID")
    unit_id: str = Field(..., description="Unit ID")
    unit: HousingUnit = Field(..., description="Housing unit details")
    score: MatchScore = Field(..., description="Match scores")
    explanation: Optional[str] = Field(None, description="Match explanation")
    document_checklist: List[str] = Field(default_factory=list, description="Required documents")
    application_steps: List[str] = Field(default_factory=list, description="Application steps")
    matched_at: datetime = Field(default_factory=datetime.utcnow, description="Match timestamp")
    expires_at: datetime = Field(..., description="Match expiry date")
    
    class Config:
        from_attributes = True


class HousingApplication(BaseModel):
    """Housing application details"""
    application_id: str = Field(..., description="Application ID")
    family_id: str = Field(..., description="Family ID")
    unit_id: str = Field(..., description="Unit ID")
    status: ApplicationStatus = Field(..., description="Application status")
    submitted_at: datetime = Field(..., description="Submission date")
    submitted_by: str = Field(..., description="Submitted by user ID")
    
    # Application data
    family_profile: FamilyProfile = Field(..., description="Family profile at time of application")
    unit_details: HousingUnit = Field(..., description="Unit details at time of application")
    documents_submitted: List[str] = Field(default_factory=list, description="Submitted documents")
    documents_pending: List[str] = Field(default_factory=list, description="Pending documents")
    
    # Processing details
    current_stage: str = Field(..., description="Current processing stage")
    next_steps: List[str] = Field(default_factory=list, description="Next steps")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion date")
    
    # Review details
    reviewed_by: Optional[str] = Field(None, description="Reviewed by officer ID")
    reviewed_at: Optional[datetime] = Field(None, description="Review date")
    review_comments: Optional[str] = Field(None, description="Review comments")
    
    # Decision details
    decision_by: Optional[str] = Field(None, description="Decision made by")
    decision_at: Optional[datetime] = Field(None, description="Decision date")
    decision_reasons: List[str] = Field(default_factory=list, description="Decision reasons")
    
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class HousingPriority(BaseModel):
    """Housing priority and recommendations"""
    priority_level: str = Field(..., description="Priority level")
    top_priority_area: str = Field(..., description="Top priority area")
    recommendations: List[str] = Field(..., description="Recommendations")
    estimated_cost_range: str = Field(..., description="Estimated cost range")
    implementation_timeline: str = Field(..., description="Implementation timeline")
    
    class Config:
        from_attributes = True


class HousingAnalytics(BaseModel):
    """Housing analytics data"""
    total_applications: int = Field(..., description="Total applications")
    total_matches: int = Field(..., description="Total matches")
    by_category: Dict[str, int] = Field(..., description="Applications by category")
    by_status: Dict[str, int] = Field(..., description="Applications by status")
    avg_match_score: float = Field(..., description="Average match score")
    conversion_rate: float = Field(..., description="Application conversion rate")
    processing_time_avg: float = Field(..., description="Average processing time in days")
    success_rate: float = Field(..., description="Success rate percentage")
    
    class Config:
        from_attributes = True


class HousingInsight(BaseModel):
    """AI-generated housing insight"""
    insight_type: str = Field(..., description="Type of insight")
    description: str = Field(..., description="Insight description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    actionable: bool = Field(..., description="Whether insight is actionable")
    recommendation: Optional[str] = Field(None, description="Recommended action")
    
    class Config:
        from_attributes = True


class HousingReport(BaseModel):
    """Comprehensive housing report"""
    report_date: datetime = Field(..., description="Report date")
    analytics: HousingAnalytics = Field(..., description="Housing analytics")
    insights: List[HousingInsight] = Field(..., description="AI-generated insights")
    recommendations: List[str] = Field(..., description="Recommendations")
    top_performing_categories: List[str] = Field(..., description="Top performing categories")
    areas_for_improvement: List[str] = Field(..., description="Areas needing improvement")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    
    class Config:
        from_attributes = True


class HousingMatchRequest(BaseModel):
    """Request model for housing matching"""
    family_id: str = Field(..., description="Family ID")
    family_profile: FamilyProfile = Field(..., description="Family profile data")
    search_radius_km: float = Field(default=10.0, description="Search radius in kilometers")
    max_results: int = Field(default=10, description="Maximum results to return")
    include_unavailable: bool = Field(default=False, description="Include unavailable units")


class HousingMatchResponse(BaseModel):
    """Response model for housing matching"""
    success: bool = Field(..., description="Request success status")
    matches: List[HousingMatch] = Field(..., description="Housing matches")
    message: str = Field(..., description="Response message")
    total_found: int = Field(..., description="Total matches found")
    processing_time: float = Field(..., description="Processing time in seconds")
    
    class Config:
        from_attributes = True


class HousingStatistics(BaseModel):
    """Housing system statistics"""
    total_units: int = Field(..., description="Total housing units")
    available_units: int = Field(..., description="Available units")
    occupied_units: int = Field(..., description="Occupied units")
    total_applications: int = Field(..., description="Total applications")
    pending_applications: int = Field(..., description="Pending applications")
    approved_applications: int = Field(..., description="Approved applications")
    rejected_applications: int = Field(..., description="Rejected applications")
    average_match_score: float = Field(..., description="Average match score")
    average_time_to_match: float = Field(..., description="Average time to match in days")
    conversion_rate: float = Field(..., description="Application conversion rate")
    category_distribution: Dict[str, int] = Field(..., description="Distribution by category")
    status_distribution: Dict[str, int] = Field(..., description="Distribution by status")
    
    class Config:
        from_attributes = True

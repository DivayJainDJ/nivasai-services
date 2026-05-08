"""
Pydantic schemas for ward-related data structures
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class WardPriority(str, Enum):
    """Ward priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InfrastructureType(str, Enum):
    """Infrastructure types"""
    ROAD_CONNECTIVITY = "road_connectivity"
    WATER_ACCESS = "water_access"
    SANITATION_COVERAGE = "sanitation_coverage"
    ELECTRICITY_ACCESS = "electricity_access"
    GREEN_COVERAGE = "green_coverage"
    INFORMAL_SETTLEMENTS = "informal_settlements"


class WardScore(BaseModel):
    """Infrastructure scores for a ward"""
    road_connectivity: float = Field(..., ge=0.0, le=10.0, description="Road connectivity score (0-10)")
    water_access: float = Field(..., ge=0.0, le=10.0, description="Water access score (0-10)")
    sanitation_coverage: float = Field(..., ge=0.0, le=10.0, description="Sanitation coverage score (0-10)")
    electricity_access: float = Field(..., ge=0.0, le=10.0, description="Electricity access score (0-10)")
    green_coverage: float = Field(..., ge=0.0, le=10.0, description="Green coverage score (0-10)")
    informal_settlements: float = Field(..., ge=0.0, le=10.0, description="Informal settlements score (0-10)")
    overall_score: float = Field(..., ge=0.0, le=10.0, description="Overall infrastructure score (0-10)")
    
    @validator('overall_score')
    def validate_overall_score(cls, v, values):
        """Validate overall score is average of components"""
        if 'road_connectivity' in values and 'water_access' in values:
            expected = sum([
                values['road_connectivity'],
                values['water_access'],
                values['sanitation_coverage'],
                values['electricity_access'],
                values['green_coverage'],
                values['informal_settlements']
            ]) / 6
            if abs(v - expected) > 0.1:
                raise ValueError('Overall score should be average of component scores')
        return v


class PriorityAnalysis(BaseModel):
    """Priority analysis for ward improvements"""
    priority_level: WardPriority = Field(..., description="Priority level")
    top_priority_area: str = Field(..., description="Top priority infrastructure area")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    estimated_cost_range: str = Field(..., description="Estimated cost range for improvements")
    implementation_timeline: str = Field(..., description="Estimated implementation timeline")
    urgency_factors: List[str] = Field(default_factory=list, description="Factors contributing to urgency")


class DemographicAnalysis(BaseModel):
    """Demographic analysis for ward"""
    estimated_population: int = Field(..., ge=0, description="Estimated population")
    population_density_per_sqkm: int = Field(..., ge=0, description="Population density per sq km")
    household_count: int = Field(..., ge=0, description="Number of households")
    income_level: str = Field(..., description="Income level classification")
    education_level: str = Field(..., description="Education level classification")
    employment_sectors: List[str] = Field(default_factory=list, description="Main employment sectors")
    vulnerable_groups: List[str] = Field(default_factory=list, description="Vulnerable groups present")


class AIAnalysis(BaseModel):
    """AI analysis results"""
    scores: Dict[str, float] = Field(default_factory=dict, description="AI-generated scores")
    summary: str = Field(..., description="AI-generated summary")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")
    visual_elements: List[str] = Field(default_factory=list, description="Visual elements detected")
    detected_objects: List[str] = Field(default_factory=list, description="Objects detected in imagery")
    technical_details: Dict[str, Any] = Field(default_factory=dict, description="Technical analysis details")


class WardAnalysis(BaseModel):
    """Complete ward analysis"""
    ward_id: str = Field(..., description="Ward ID")
    ward_name: str = Field(..., description="Ward name")
    coordinates: Dict[str, float] = Field(..., description="Ward center coordinates")
    analysis_type: str = Field(..., description="Type of analysis performed")
    scores: WardScore = Field(..., description="Infrastructure scores")
    priority_analysis: PriorityAnalysis = Field(..., description="Priority analysis")
    demographic_analysis: DemographicAnalysis = Field(..., description="Demographic analysis")
    ai_analysis: AIAnalysis = Field(..., description="AI analysis results")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    processing_time_seconds: float = Field(..., description="Processing time in seconds")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    data_sources: List[str] = Field(default_factory=list, description="Data sources used")
    
    class Config:
        from_attributes = True


class WardAnalysisRequest(BaseModel):
    """Request model for ward analysis"""
    ward_id: str = Field(..., description="Ward ID")
    ward_name: str = Field(..., description="Ward name")
    coordinates: Dict[str, float] = Field(..., description="Ward coordinates {lat, lng}")
    analysis_type: str = Field(default="comprehensive", description="Analysis type")
    include_recommendations: bool = Field(default=True, description="Include recommendations")
    search_radius_km: float = Field(default=10.0, description="Search radius for analysis")


class WardAnalysisResponse(BaseModel):
    """Response model for ward analysis"""
    success: bool = Field(..., description="Request success status")
    analysis_id: Optional[str] = Field(None, description="Analysis ID")
    message: str = Field(..., description="Response message")
    data: Optional[WardAnalysis] = Field(None, description="Analysis data")


class RemediationProject(BaseModel):
    """Remediation project for ward"""
    project_id: str = Field(..., description="Project ID")
    ward_id: str = Field(..., description="Ward ID")
    name: str = Field(..., description="Project name")
    category: str = Field(..., description="Project category")
    priority: str = Field(..., description="Project priority")
    estimated_cost: str = Field(..., description="Estimated cost")
    timeline: str = Field(..., description="Implementation timeline")
    description: str = Field(..., description="Project description")
    status: str = Field(default="proposed", description="Project status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class WardComparison(BaseModel):
    """Ward comparison data"""
    ward_id: str = Field(..., description="Ward ID")
    ward_name: str = Field(..., description="Ward name")
    overall_score: float = Field(..., description="Overall infrastructure score")
    priority_level: WardPriority = Field(..., description="Priority level")
    top_priority_area: str = Field(..., description="Top priority area")
    project_count: int = Field(..., description="Number of remediation projects")
    rank: int = Field(..., description="Rank in comparison")
    
    class Config:
        from_attributes = True


class WardTrend(BaseModel):
    """Ward trend data point"""
    date: datetime = Field(..., description="Date of data point")
    overall_score: float = Field(..., description="Overall score")
    complaint_count: int = Field(..., description="Number of complaints")
    resolution_rate: float = Field(..., description="Resolution rate percentage")
    
    class Config:
        from_attributes = True


class WardMetrics(BaseModel):
    """Ward performance metrics"""
    ward_id: str = Field(..., description="Ward ID")
    ward_name: str = Field(..., description="Ward name")
    complaint_count: int = Field(..., description="Number of complaints")
    infrastructure_score: float = Field(..., description="Infrastructure score")
    priority_level: WardPriority = Field(..., description="Priority level")
    last_analyzed: datetime = Field(..., description="Last analysis date")
    performance_trend: str = Field(..., description="Performance trend")
    
    class Config:
        from_attributes = True


class WardRanking(BaseModel):
    """Ward ranking data"""
    rank: int = Field(..., description="Rank position")
    ward_id: str = Field(..., description="Ward ID")
    ward_name: str = Field(..., description="Ward name")
    overall_score: float = Field(..., description="Overall score")
    priority_level: WardPriority = Field(..., description="Priority level")
    change_in_rank: int = Field(..., description="Change in rank from previous period")
    
    class Config:
        from_attributes = True


class WardAnalytics(BaseModel):
    """Complete ward analytics"""
    total_wards: int = Field(..., description="Total number of wards")
    ward_metrics: Dict[str, WardMetrics] = Field(..., description="Metrics by ward")
    top_performing_wards: List[WardMetrics] = Field(..., description="Top performing wards")
    needs_attention_wards: List[WardMetrics] = Field(..., description="Wards needing attention")
    avg_infrastructure_score: float = Field(..., description="Average infrastructure score")
    priority_distribution: Dict[str, int] = Field(..., description="Distribution of priority levels")
    trend_analysis: Dict[str, Any] = Field(..., description="Trend analysis data")
    
    class Config:
        from_attributes = True


class WardInsight(BaseModel):
    """AI-generated insight about ward"""
    insight_type: str = Field(..., description="Type of insight")
    description: str = Field(..., description="Insight description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    actionable: bool = Field(..., description="Whether insight is actionable")
    recommendation: Optional[str] = Field(None, description="Recommended action")
    
    class Config:
        from_attributes = True


class WardReport(BaseModel):
    """Comprehensive ward report"""
    ward_id: str = Field(..., description="Ward ID")
    report_date: datetime = Field(..., description="Report date")
    analysis: WardAnalysis = Field(..., description="Ward analysis")
    projects: List[RemediationProject] = Field(..., description="Remediation projects")
    insights: List[WardInsight] = Field(..., description="AI-generated insights")
    recommendations: List[str] = Field(..., description="Recommendations")
    next_steps: List[str] = Field(..., description="Next steps")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    
    class Config:
        from_attributes = True

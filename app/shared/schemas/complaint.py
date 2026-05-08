"""
Pydantic schemas for complaint-related data structures
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ComplaintCategory(str, Enum):
    """Complaint categories"""
    WATER = "water"
    SANITATION = "sanitation"
    ROADS = "roads"
    ELECTRICITY = "electricity"
    WASTE = "waste"
    EVICTION = "eviction"
    HOUSING = "housing"
    STREET_LIGHTS = "street_lights"
    DRAINAGE = "drainage"
    PARKS = "parks"
    NOISE = "noise"
    OTHER = "other"


class ComplaintSeverity(str, Enum):
    """Complaint severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplaintStatus(str, Enum):
    """Complaint status"""
    PENDING = "pending"
    CLASSIFIED = "classified"
    ROUTED = "routed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    REJECTED = "rejected"
    CLOSED = "closed"


class Department(str, Enum):
    """Government departments"""
    WATER = "water"
    SANITATION = "sanitation"
    ROADS = "roads"
    ELECTRICITY = "electricity"
    MUNICIPAL = "municipal"
    HOUSING = "housing"
    HEALTH = "health"
    EDUCATION = "education"
    POLICE = "police"
    FIRE = "fire"


class Location(BaseModel):
    """Location information"""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    address: str = Field(..., description="Full address")
    landmark: Optional[str] = Field(None, description="Nearby landmark")
    pincode: str = Field(..., description="Postal code")
    ward_id: str = Field(..., description="Ward ID")
    
    @validator('pincode')
    def validate_pincode(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('Pincode must be a 6-digit number')
        return v


class ComplaintMedia(BaseModel):
    """Media attached to complaint"""
    type: str = Field(..., description="Media type: image, video, document")
    url: str = Field(..., description="Media URL")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class ComplaintClassification(BaseModel):
    """AI classification result"""
    category: ComplaintCategory
    severity: ComplaintSeverity
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    summary: str = Field(..., description="AI-generated summary")
    suggested_department: Department
    keywords: List[str] = Field(default_factory=list)
    classified_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0.5:
            raise ValueError('Confidence must be at least 0.5 for reliable classification')
        return v


class ComplaintRouting(BaseModel):
    """Complaint routing information"""
    officer_id: str
    officer_name: str
    department: Department
    routed_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_resolution_time: Optional[int] = Field(None, description="Estimated resolution time in hours")
    priority_score: float = Field(..., ge=0.0, le=1.0, description="Routing priority score")


class ComplaintEscalation(BaseModel):
    """Complaint escalation details"""
    escalated_at: datetime = Field(default_factory=datetime.utcnow)
    reason: str
    escalated_to: str  # Officer ID
    escalated_by: str  # Officer ID
    previous_level: int
    new_level: int
    deadline: datetime


class ComplaintCreate(BaseModel):
    """Schema for creating a new complaint"""
    user_id: str = Field(..., description="User ID who filed the complaint")
    title: str = Field(..., min_length=5, max_length=200, description="Complaint title")
    description: str = Field(..., min_length=10, max_length=2000, description="Detailed description")
    location: Location
    category: Optional[ComplaintCategory] = Field(None, description="User-suggested category")
    severity: Optional[ComplaintSeverity] = Field(None, description="User-suggested severity")
    media_urls: List[str] = Field(default_factory=list, description="Media URLs")
    is_anonymous: bool = Field(False, description="Whether complaint is anonymous")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    
    @validator('contact_phone')
    def validate_phone(cls, v):
        if v and not v.isdigit():
            raise ValueError('Phone number must contain only digits')
        return v


class ComplaintUpdate(BaseModel):
    """Schema for updating a complaint"""
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    location: Optional[Location] = None
    status: Optional[ComplaintStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = Field(None, max_length=1000)


class ComplaintResponse(BaseModel):
    """Schema for complaint response"""
    complaint_id: str
    user_id: str
    title: str
    description: str
    location: Location
    status: ComplaintStatus
    category: Optional[ComplaintCategory] = None
    severity: Optional[ComplaintSeverity] = None
    priority: int = Field(default=5, ge=1, le=10)
    classification: Optional[ComplaintClassification] = None
    routing: Optional[ComplaintRouting] = None
    escalation: Optional[ComplaintEscalation] = None
    media: List[ComplaintMedia] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class ComplaintFilter(BaseModel):
    """Schema for filtering complaints"""
    user_id: Optional[str] = None
    ward_id: Optional[str] = None
    category: Optional[ComplaintCategory] = None
    severity: Optional[ComplaintSeverity] = None
    status: Optional[ComplaintStatus] = None
    department: Optional[Department] = None
    officer_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    priority_min: Optional[int] = Field(None, ge=1, le=10)
    priority_max: Optional[int] = Field(None, ge=1, le=10)
    
    class Config:
        extra = "allow"  # Allow additional filter parameters


class ComplaintAnalytics(BaseModel):
    """Complaint analytics data"""
    total_complaints: int
    complaints_by_category: Dict[str, int]
    complaints_by_severity: Dict[str, int]
    complaints_by_status: Dict[str, int]
    complaints_by_ward: Dict[str, int]
    avg_resolution_time: Optional[float] = None  # in hours
    resolution_rate: Optional[float] = None  # percentage
    escalation_rate: Optional[float] = None  # percentage
    
    class Config:
        from_attributes = True


class ComplaintStats(BaseModel):
    """Complaint statistics for dashboard"""
    today: int
    this_week: int
    this_month: int
    pending: int
    in_progress: int
    resolved: int
    escalated: int
    avg_resolution_time: Optional[float] = None
    
    class Config:
        from_attributes = True


class ComplaintBulkCreate(BaseModel):
    """Schema for bulk complaint creation"""
    complaints: List[ComplaintCreate] = Field(..., min_items=1, max_items=100)
    
    @validator('complaints')
    def validate_complaints(cls, v):
        if len(v) > 100:
            raise ValueError('Cannot create more than 100 complaints at once')
        return v


class ComplaintSearch(BaseModel):
    """Schema for complaint search"""
    query: str = Field(..., min_length=2, max_length=100)
    filters: Optional[ComplaintFilter] = None
    sort_by: Optional[str] = Field("created_at", description="Field to sort by")
    sort_order: Optional[str] = Field("desc", description="Sort order: asc or desc")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
    class Config:
        extra = "allow"


class ComplaintNotification(BaseModel):
    """Schema for complaint notifications"""
    complaint_id: str
    user_id: str
    type: str  # created, updated, resolved, escalated
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ComplaintExport(BaseModel):
    """Schema for complaint export"""
    format: str = Field("csv", description="Export format: csv, xlsx, json")
    filters: Optional[ComplaintFilter] = None
    fields: Optional[List[str]] = Field(None, description="Fields to include")
    
    @validator('format')
    def validate_format(cls, v):
        if v not in ['csv', 'xlsx', 'json']:
            raise ValueError('Format must be csv, xlsx, or json')
        return v

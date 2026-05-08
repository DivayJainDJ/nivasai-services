"""
Pydantic schemas for WhatsApp-related data structures
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class MessageDirection(str, Enum):
    """Message direction"""
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class IntentType(str, Enum):
    """WhatsApp intent types"""
    COMPLAINT_REGISTER = "complaint_register"
    COMPLAINT_STATUS = "complaint_status"
    HOUSING_QUERY = "housing_query"
    WARD_INFO = "ward_info"
    HELP = "help"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class ConversationState(str, Enum):
    """Conversation states"""
    GREETING = "greeting"
    AWAITING_COMPLAINT_TYPE = "awaiting_complaint_type"
    AWAITING_LOCATION = "awaiting_location"
    AWAITING_DETAILS = "awaiting_details"
    CONFIRMATION = "confirmation"
    FOLLOW_UP = "follow_up"


class WhatsAppMessage(BaseModel):
    """WhatsApp message model"""
    message_id: str = Field(..., description="Unique message ID")
    from_number: str = Field(..., description="Sender phone number")
    message_body: str = Field(..., description="Message text content")
    media_url: Optional[str] = Field(None, description="Media attachment URL")
    direction: MessageDirection = Field(..., description="Message direction")
    timestamp: datetime = Field(..., description="Message timestamp")
    
    @validator('from_number')
    def validate_phone_number(cls, v):
        """Validate phone number format"""
        # Remove any non-digit characters
        clean_number = ''.join(filter(str.isdigit, v))
        if len(clean_number) < 10 or len(clean_number) > 15:
            raise ValueError('Invalid phone number')
        return v
    
    class Config:
        from_attributes = True


class ConversationContext(BaseModel):
    """Conversation context"""
    conversation_id: str = Field(..., description="Unique conversation ID")
    phone_number: str = Field(..., description="User phone number")
    state: ConversationState = Field(..., description="Current conversation state")
    context: Dict[str, Any] = Field(default_factory=dict, description="Conversation context data")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Conversation start time")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    message_count: int = Field(default=0, description="Total message count")
    
    class Config:
        from_attributes = True


class IntentDetection(BaseModel):
    """Intent detection result"""
    intent_type: IntentType = Field(..., description="Detected intent type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    response_suggestion: Optional[str] = Field(None, description="Suggested response")
    detection_method: str = Field(default="ai", description="Detection method (ai/rule_based)")
    
    class Config:
        from_attributes = True


class WhatsAppResponse(BaseModel):
    """WhatsApp response model"""
    response_text: str = Field(..., description="Response text")
    should_reply: bool = Field(default=True, description="Whether to send reply")
    media_urls: List[str] = Field(default_factory=list, description="Media URLs to send")
    next_state: Optional[ConversationState] = Field(None, description="Next conversation state")
    intent_processed: bool = Field(default=True, description="Whether intent was processed")
    complaint_id: Optional[str] = Field(None, description="Generated complaint ID")
    
    class Config:
        from_attributes = True


class ConversationEvent(BaseModel):
    """Conversation event for logging"""
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: str = Field(..., description="Message ID")
    message_body: str = Field(..., description="Message content")
    direction: MessageDirection = Field(..., description="Message direction")
    intent_type: IntentType = Field(..., description="Detected intent")
    intent_confidence: float = Field(..., description="Intent confidence")
    response_sent: bool = Field(..., description="Whether response was sent")
    timestamp: datetime = Field(..., description="Event timestamp")
    
    class Config:
        from_attributes = True


class WhatsAppAnalytics(BaseModel):
    """WhatsApp analytics data"""
    total_messages: int = Field(..., description="Total messages")
    incoming_messages: int = Field(..., description="Incoming messages")
    outgoing_messages: int = Field(..., description="Outgoing messages")
    by_intent: Dict[str, int] = Field(..., description="Messages by intent type")
    avg_confidence: float = Field(..., description="Average intent confidence")
    response_rate: float = Field(..., description="Response rate percentage")
    active_users: int = Field(..., description="Number of active users")
    responses_sent: int = Field(..., description="Total responses sent")
    avg_response_time: float = Field(..., description="Average response time in seconds")
    
    class Config:
        from_attributes = True


class WhatsAppTemplate(BaseModel):
    """WhatsApp message template"""
    template_id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    content: str = Field(..., description="Template content")
    variables: List[str] = Field(default_factory=list, description="Template variables")
    category: str = Field(..., description="Template category")
    language: str = Field(default="en", description="Template language")
    
    class Config:
        from_attributes = True


class WhatsAppBroadcast(BaseModel):
    """WhatsApp broadcast message"""
    broadcast_id: str = Field(..., description="Broadcast ID")
    message_text: str = Field(..., description="Message content")
    recipients: List[str] = Field(..., description="Recipient phone numbers")
    sent_by: str = Field(..., description="User who sent broadcast")
    sent_at: datetime = Field(default_factory=datetime.utcnow, description="Send timestamp")
    status: str = Field(default="pending", description="Broadcast status")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Send results")
    
    class Config:
        from_attributes = True


class WhatsAppInsight(BaseModel):
    """AI-generated WhatsApp insight"""
    insight_type: str = Field(..., description="Type of insight")
    description: str = Field(..., description="Insight description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    actionable: bool = Field(..., description="Whether insight is actionable")
    recommendation: Optional[str] = Field(None, description="Recommended action")
    
    class Config:
        from_attributes = True


class WhatsAppReport(BaseModel):
    """WhatsApp performance report"""
    report_date: datetime = Field(..., description="Report date")
    analytics: WhatsAppAnalytics = Field(..., description="Analytics data")
    insights: List[WhatsAppInsight] = Field(..., description="AI-generated insights")
    top_intents: List[str] = Field(..., description="Top intent types")
    performance_metrics: Dict[str, float] = Field(..., description="Performance metrics")
    recommendations: List[str] = Field(..., description="Recommendations")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    
    class Config:
        from_attributes = True


class WhatsAppUser(BaseModel):
    """WhatsApp user profile"""
    phone_number: str = Field(..., description="User phone number")
    name: Optional[str] = Field(None, description="User name")
    preferred_language: str = Field(default="en", description="Preferred language")
    ward_id: Optional[str] = Field(None, description="User's ward ID")
    first_seen: datetime = Field(default_factory=datetime.utcnow, description="First interaction")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="Last interaction")
    total_messages: int = Field(default=0, description="Total messages sent")
    complaints_registered: int = Field(default=0, description="Complaints registered")
    housing_queries: int = Field(default=0, description="Housing queries made")
    
    class Config:
        from_attributes = True


class WhatsAppQueue(BaseModel):
    """Message queue for processing"""
    queue_id: str = Field(..., description="Queue ID")
    phone_number: str = Field(..., description="Recipient phone number")
    message_text: str = Field(..., description="Message content")
    media_urls: List[str] = Field(default_factory=list, description="Media URLs")
    priority: int = Field(default=5, ge=1, le=10, description="Message priority")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled send time")
    attempts: int = Field(default=0, description="Send attempts")
    max_attempts: int = Field(default=3, description="Maximum attempts")
    status: str = Field(default="pending", description="Queue status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Queue creation time")
    sent_at: Optional[datetime] = Field(None, description="Actual send time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        from_attributes = True


class WhatsAppWebhook(BaseModel):
    """WhatsApp webhook payload"""
    message_sid: str = Field(..., description="Message SID")
    account_sid: str = Field(..., description="Account SID")
    from_number: str = Field(..., description="Sender number")
    to_number: str = Field(..., description="Recipient number")
    body: str = Field(..., description="Message body")
    num_media: int = Field(default=0, description="Number of media items")
    media_urls: List[str] = Field(default_factory=list, description="Media URLs")
    timestamp: datetime = Field(..., description="Message timestamp")
    
    class Config:
        from_attributes = True


class WhatsAppConfig(BaseModel):
    """WhatsApp service configuration"""
    twilio_account_sid: str = Field(..., description="Twilio Account SID")
    twilio_auth_token: str = Field(..., description="Twilio Auth Token")
    whatsapp_number: str = Field(..., description="WhatsApp number")
    webhook_url: str = Field(..., description="Webhook URL")
    max_queue_size: int = Field(default=1000, description="Maximum queue size")
    retry_attempts: int = Field(default=3, description="Retry attempts")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")
    
    class Config:
        from_attributes = True

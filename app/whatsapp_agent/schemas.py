"""Pydantic schemas for WhatsApp agent."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class IntentClassification(BaseModel):
    """Intent classification result."""

    intent: Literal[
        "complaint_submission",
        "complaint_status",
        "housing_help",
        "escalation_help",
        "ward_information",
        "greeting",
        "unknown",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    language: Literal["en", "hi"] = "en"
    entities: dict = Field(default_factory=dict)


class ConversationState(BaseModel):
    """Conversation state for a user."""

    phoneNumber: str
    lastIntent: Optional[str] = None
    activeWorkflow: Optional[str] = None
    workflowData: dict = Field(default_factory=dict)
    preferredLanguage: Literal["en", "hi"] = "en"
    conversationHistory: list[dict] = Field(default_factory=list)
    lastMessageAt: Optional[datetime] = None
    createdAt: Optional[datetime] = None


class WhatsAppMessage(BaseModel):
    """Incoming WhatsApp message."""

    From: str  # Phone number with whatsapp: prefix
    Body: str = ""
    NumMedia: int = 0
    MediaUrl0: Optional[str] = None
    MediaContentType0: Optional[str] = None
    MessageSid: str = ""


class WhatsAppResponse(BaseModel):
    """Outgoing WhatsApp response."""

    message: str
    mediaUrl: Optional[str] = None


class ComplaintAcknowledgment(BaseModel):
    """Complaint creation acknowledgment."""

    complaintId: str
    category: str
    severity: str
    estimatedResolutionDays: int
    assignedDepartment: str
    message: str


class StatusUpdate(BaseModel):
    """Complaint status update."""

    complaintId: str
    status: str
    assignedOfficer: Optional[str] = None
    lastUpdate: str
    escalationLevel: Optional[str] = None
    message: str


class HousingRecommendation(BaseModel):
    """Housing recommendation summary."""

    unitId: str
    scheme: str
    priceINR: int
    distanceKm: float
    score: float
    shortDescription: str

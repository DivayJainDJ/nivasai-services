"""Pydantic schemas for bot webhook."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TwilioWebhookPayload(BaseModel):
    """Twilio WhatsApp webhook payload."""

    Body: str = ""
    From: str
    To: Optional[str] = None
    MessageSid: Optional[str] = None
    NumMedia: str = "0"
    MediaUrl0: Optional[str] = None
    MediaContentType0: Optional[str] = None
    ProfileName: Optional[str] = None


class IntentClassification(BaseModel):
    """Intent classification result."""

    intent: Literal[
        "FILE_COMPLAINT",
        "CHECK_STATUS",
        "FIND_HOUSING",
        "DOCUMENT_UPLOAD",
        "WARD_INFO",
        "GREET",
        "UNKNOWN",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    language: Literal["en", "hi"] = "en"
    entities: dict[str, Any] = Field(default_factory=dict)


class BotSession(BaseModel):
    """Bot conversation session."""

    phone: str
    currentIntent: Optional[str] = None
    workflowState: Optional[str] = None
    preferredLanguage: Literal["en", "hi"] = "en"
    conversationHistory: list[dict[str, str]] = Field(default_factory=list)
    contextData: dict[str, Any] = Field(default_factory=dict)
    lastUpdated: datetime = Field(default_factory=datetime.utcnow)
    createdAt: datetime = Field(default_factory=datetime.utcnow)


class HandlerResponse(BaseModel):
    """Handler response."""

    message: str
    success: bool = True
    nextState: Optional[str] = None
    contextUpdate: dict[str, Any] = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    """Webhook response."""

    message: str
    status: str = "success"
    intent: Optional[str] = None

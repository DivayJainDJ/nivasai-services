"""Notification broadcaster schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class NotificationPayload(BaseModel):
    """Pub/Sub notification payload."""

    title: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1, max_length=500)
    type: str = Field(..., min_length=1)
    priority: str = Field(default="normal")
    targetRoles: List[str] = Field(default_factory=list)
    targetWards: List[str] = Field(default_factory=list)
    targetDepartments: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority."""
        if v not in ["normal", "high"]:
            raise ValueError("Priority must be 'normal' or 'high'")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title length."""
        if len(v) > 100:
            raise ValueError("Title must be 100 characters or less")
        return v

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        """Validate body length."""
        if len(v) > 500:
            raise ValueError("Body must be 500 characters or less")
        return v


class FCMToken(BaseModel):
    """FCM token document."""

    userId: str
    role: str
    ward: Optional[str] = None
    department: Optional[str] = None
    token: str
    active: bool = True
    lastSeen: datetime
    createdAt: Optional[datetime] = None


class FCMMessage(BaseModel):
    """FCM message format."""

    notification: Dict[str, str]
    data: Dict[str, str]
    android: Optional[Dict[str, Any]] = None
    apns: Optional[Dict[str, Any]] = None
    token: str


class BatchSendResult(BaseModel):
    """Batch send result."""

    successCount: int = 0
    failureCount: int = 0
    invalidTokens: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class NotificationLog(BaseModel):
    """Notification delivery log."""

    notificationId: str
    title: str
    body: str
    type: str
    priority: str
    targetRoles: List[str]
    targetWards: List[str]
    targetDepartments: List[str]
    successCount: int
    failureCount: int
    invalidTokensRemoved: int
    sentAt: datetime
    completedAt: Optional[datetime] = None
    errors: List[str] = Field(default_factory=list)


class TokenFilter(BaseModel):
    """Token filter criteria."""

    roles: List[str] = Field(default_factory=list)
    wards: List[str] = Field(default_factory=list)
    departments: List[str] = Field(default_factory=list)
    activeOnly: bool = True

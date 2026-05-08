"""
WhatsApp chatbot schema.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class WhatsAppIntent(BaseModel):
    """Detected WhatsApp user intent."""

    intent_type: str  # complaint, status_query, help, other
    confidence: float = Field(ge=0, le=1)
    entities: Dict[str, Any]
    extracted_data: Optional[Dict[str, str]] = None


class WhatsAppMessage(BaseModel):
    """WhatsApp message for processing."""

    message_id: str
    sender_id: str
    text: str
    timestamp: str
    media_url: Optional[str] = None

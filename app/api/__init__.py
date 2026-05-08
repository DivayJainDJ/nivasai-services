"""
WhatsApp webhook endpoint.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.whatsapp_agent.service import process_message

router = APIRouter()


class WhatsAppWebhookPayload(BaseModel):
    """WhatsApp webhook payload."""

    sender_id: str
    message_text: str


@router.post("/whatsappWebhook")
async def whatsapp_webhook(payload: WhatsAppWebhookPayload):
    """Handle WhatsApp chatbot webhook."""
    try:
        response = process_message(payload.sender_id, payload.message_text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

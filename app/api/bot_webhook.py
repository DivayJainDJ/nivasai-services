"""Bot webhook API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import PlainTextResponse

from app.bot_webhook.schemas import TwilioWebhookPayload
from app.bot_webhook.service import BotWebhookService
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/bot/webhook", response_class=PlainTextResponse)
async def bot_webhook(
    Body: str = Form(""),
    From: str = Form(...),
    To: str = Form(""),
    MessageSid: str = Form(""),
    NumMedia: str = Form("0"),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None),
    ProfileName: str = Form(None),
) -> str:
    """
    Handle incoming WhatsApp messages from Twilio.
    
    This is the public webhook endpoint that receives all WhatsApp messages.
    
    Args:
        Body: Message text
        From: Sender phone number (whatsapp:+919999999999)
        To: Recipient number
        MessageSid: Message ID
        NumMedia: Number of media attachments
        MediaUrl0: First media URL
        MediaContentType0: First media content type
        ProfileName: User's WhatsApp profile name
    
    Returns:
        TwiML response or plain text
    """
    try:
        # Create payload
        payload = TwilioWebhookPayload(
            Body=Body,
            From=From,
            To=To,
            MessageSid=MessageSid,
            NumMedia=NumMedia,
            MediaUrl0=MediaUrl0,
            MediaContentType0=MediaContentType0,
            ProfileName=ProfileName,
        )
        
        logger.info(
            "webhook_request",
            from_number=From,
            message_length=len(Body),
            has_media=int(NumMedia) > 0,
        )
        
        # Process webhook
        service = BotWebhookService()
        response = service.process_webhook(payload)
        
        # Return TwiML response
        # Twilio expects plain text or TwiML
        return response.message
    
    except Exception as exc:
        logger.error("webhook_endpoint_failed", error=str(exc))
        return "Sorry, something went wrong. Please try again."


@router.get("/bot/health")
async def bot_health() -> dict:
    """Health check for bot webhook."""
    return {
        "status": "healthy",
        "service": "bot_webhook",
        "version": "1.0.0",
    }

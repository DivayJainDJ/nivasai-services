"""WhatsApp webhook API endpoint for Twilio integration."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import Response

from app.whatsapp_agent.service import WhatsAppAgentError, process_whatsapp_message
from app.whatsapp_agent.schemas import WhatsAppMessage

router = APIRouter()


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    NumMedia: int = Form(0),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None),
    MessageSid: str = Form(""),
):
    """
    Twilio WhatsApp webhook endpoint.
    
    Receives incoming WhatsApp messages from Twilio and processes them.
    Returns TwiML response for Twilio.
    """
    try:
        # Create WhatsApp message object
        message = WhatsAppMessage(
            From=From,
            Body=Body,
            NumMedia=NumMedia,
            MediaUrl0=MediaUrl0,
            MediaContentType0=MediaContentType0,
            MessageSid=MessageSid,
        )
        
        # Process message
        response = process_whatsapp_message(message)
        
        # Return TwiML response
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response.message}</Message>
</Response>"""
        
        return Response(content=twiml, media_type="application/xml")
    
    except WhatsAppAgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"WhatsApp processing failed: {exc}",
        ) from exc


@router.get("/whatsapp/webhook")
async def whatsapp_webhook_verify():
    """
    Webhook verification endpoint for Twilio.
    
    Twilio may send GET requests to verify the webhook URL.
    """
    return {"status": "ok", "message": "WhatsApp webhook is active"}

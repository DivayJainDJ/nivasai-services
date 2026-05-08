"""
API endpoints for WhatsApp webhook
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime
import json

from app.dependencies import get_services
from app.shared.logging.logger import get_logger
from app.shared.validators.whatsapp_validator import WhatsAppWebhookValidator

logger = get_logger(__name__)
router = APIRouter()


@router.post("/webhook", response_model=dict)
async def whatsapp_webhook(
    request: Request,
    services = Depends(get_services)
):
    """
    Handle incoming WhatsApp webhook from Twilio
    
    Args:
        request: FastAPI request object
        services: Service dependencies
        
    Returns:
        Webhook response
    """
    try:
        logger.info("Received WhatsApp webhook")
        
        # Parse Twilio webhook data
        form_data = await request.form()
        
        # Extract webhook parameters
        from_number = form_data.get('From', '').replace('whatsapp:', '')
        message_body = form_data.get('Body', '')
        message_sid = form_data.get('MessageSid', '')
        account_sid = form_data.get('AccountSid', '')
        
        # Validate webhook
        validator = WhatsAppWebhookValidator()
        validation_result = validator.validate_webhook(form_data)
        
        if not validation_result.is_valid:
            logger.error(f"Webhook validation failed: {validation_result.errors}")
            return {
                "success": False,
                "error": "Invalid webhook data"
            }
        
        # Check if this is a message delivery status
        if form_data.get('SmsStatus'):
            return await _handle_delivery_status(form_data)
        
        # Process the message
        result = await services.whatsapp_agent.process_incoming_message(
            from_number=from_number,
            message_body=message_body,
            message_timestamp=datetime.utcnow()
        )
        
        logger.info(
            "WhatsApp webhook processed",
            from_number=from_number,
            message_sid=message_sid,
            success=result.get('success', False)
        )
        
        # Return Twilio-compatible response
        return {
            "success": True,
            "message": "Webhook processed successfully"
        }
        
    except Exception as e:
        logger.error(
            "WhatsApp webhook failed",
            error=str(e),
            error_type=type(e).__name__
        )
        
        # Return error response
        return {
            "success": False,
            "error": "Webhook processing failed"
        }


async def _handle_delivery_status(form_data) -> dict:
    """Handle message delivery status updates"""
    try:
        status = form_data.get('SmsStatus')
        message_sid = form_data.get('MessageSid')
        
        logger.info(
            "WhatsApp delivery status",
            message_sid=message_sid,
            status=status
        )
        
        # This would update message status in database
        # For now, just log and return success
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Delivery status handling failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/webhook", response_model=dict)
async def verify_webhook(
    request: Request
):
    """
    Verify webhook (for Twilio webhook setup)
    
    Args:
        request: FastAPI request object
        
    Returns:
        Verification response
    """
    try:
        # Twilio expects a 200 OK response for webhook verification
        return {
            "success": True,
            "message": "Webhook verified"
        }
        
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/send", response_model=dict)
async def send_whatsapp_message(
    to_number: str,
    message_text: str,
    media_urls: Optional[list] = None,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Send WhatsApp message (admin function)
    
    Args:
        to_number: Recipient phone number
        message_text: Message content
        media_urls: Optional media URLs
        user: Current user
        services: Service dependencies
        
    Returns:
        Send result
    """
    try:
        logger.info(
            "Sending WhatsApp message",
            to_number=to_number,
            user_id=user.get('id')
        )
        
        # Validate admin permissions
        if user.get('role') not in ['admin', 'officer']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Send message
        await services.whatsapp_agent._send_whatsapp_response(
            to_number=to_number,
            message_text=message_text,
            media_urls=media_urls or []
        )
        
        return {
            "success": True,
            "message": "Message sent successfully"
        }
        
    except Exception as e:
        logger.error(
            "WhatsApp message send failed",
            to_number=to_number,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{phone_number}", response_model=dict)
async def get_conversation_history(
    phone_number: str,
    limit: int = 50,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Get conversation history for a phone number
    
    Args:
        phone_number: Phone number
        limit: Maximum messages to return
        user: Current user
        services: Service dependencies
        
    Returns:
        Conversation history
    """
    try:
        logger.info(
            "Getting conversation history",
            phone_number=phone_number,
            user_id=user.get('id')
        )
        
        # Validate permissions
        if user.get('role') not in ['admin', 'officer']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get conversation history
        conversation_id = phone_number  # Using phone number as conversation ID
        
        history = await services.whatsapp_agent._get_conversation_history(
            conversation_id, limit
        )
        
        return {
            "success": True,
            "phone_number": phone_number,
            "history": history,
            "total_messages": len(history)
        }
        
    except Exception as e:
        logger.error(
            "Failed to get conversation history",
            phone_number=phone_number,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", response_model=dict)
async def get_whatsapp_analytics(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Get WhatsApp analytics
    
    Args:
        date_from: Start date for analytics
        date_to: End date for analytics
        user: Current user
        services: Service dependencies
        
    Returns:
        WhatsApp analytics
    """
    try:
        logger.info(
            "Getting WhatsApp analytics",
            date_from=date_from,
            date_to=date_to,
            user_id=user.get('id')
        )
        
        # Validate permissions
        if user.get('role') not in ['admin', 'analyst', 'officer']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get analytics
        analytics = await services.whatsapp_agent.get_conversation_analytics(
            date_from, date_to
        )
        
        return {
            "success": True,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(
            "Failed to get WhatsApp analytics",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast", response_model=dict)
async def broadcast_message(
    message_text: str,
    recipients: list,
    user: dict = Depends(get_current_user),
    services = Depends(get_services)
):
    """
    Broadcast message to multiple recipients
    
    Args:
        message_text: Message to broadcast
        recipients: List of phone numbers
        user: Current user
        services: Service dependencies
        
    Returns:
        Broadcast result
    """
    try:
        logger.info(
            "Broadcasting WhatsApp message",
            recipients_count=len(recipients),
            user_id=user.get('id')
        )
        
        # Validate admin permissions
        if user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Validate recipients limit
        if len(recipients) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 recipients allowed")
        
        # Send broadcast
        results = []
        for phone_number in recipients:
            try:
                await services.whatsapp_agent._send_whatsapp_response(
                    to_number=phone_number,
                    message_text=message_text
                )
                results.append({"phone_number": phone_number, "status": "sent"})
            except Exception as e:
                results.append({"phone_number": phone_number, "status": "failed", "error": str(e)})
        
        sent_count = sum(1 for r in results if r["status"] == "sent")
        
        return {
            "success": True,
            "total_recipients": len(recipients),
            "sent_count": sent_count,
            "failed_count": len(recipients) - sent_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(
            "WhatsApp broadcast failed",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=dict)
async def get_message_templates(
    user: dict = Depends(get_current_user)
):
    """
    Get predefined message templates
    
    Args:
        user: Current user
        
    Returns:
        Message templates
    """
    try:
        logger.info(
            "Getting message templates",
            user_id=user.get('id')
        )
        
        # Validate permissions
        if user.get('role') not in ['admin', 'officer']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        templates = {
            "complaint_acknowledgement": "Your complaint has been registered successfully. Complaint ID: {complaint_id}",
            "status_update": "Your complaint status is now {status}. We will notify you of any changes.",
            "resolution_notification": "Great news! Your complaint {complaint_id} has been resolved. Thank you for your patience.",
            "housing_application_received": "We have received your housing application. We will process it and update you soon.",
            "housing_allotment": "Congratulations! You have been allotted housing unit {unit_id}. Please complete the formalities.",
            "general_announcement": "📢 {message}",
            "emergency_alert": "🚨 Emergency: {alert_message}. Please take necessary precautions."
        }
        
        return {
            "success": True,
            "templates": templates
        }
        
    except Exception as e:
        logger.error(
            "Failed to get message templates",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

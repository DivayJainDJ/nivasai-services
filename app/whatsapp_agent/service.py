"""Main WhatsApp agent service orchestrator."""

from __future__ import annotations

from app.shared.logging.logger import get_logger
from app.whatsapp_agent.complaint_handler import (
    ComplaintHandlerError,
    handle_complaint_submission,
    handle_text_only_complaint,
)
from app.whatsapp_agent.conversation_manager import ConversationManager
from app.whatsapp_agent.housing_handler import HousingHandlerError, handle_housing_request
from app.whatsapp_agent.intent_classifier import (
    IntentClassificationError,
    classify_intent,
    create_fallback_intent,
)
from app.whatsapp_agent.multilingual_responder import (
    generate_bilingual_response,
    generate_error_response,
    generate_greeting,
    generate_unknown_intent_response,
)
from app.whatsapp_agent.schemas import WhatsAppMessage, WhatsAppResponse
from app.whatsapp_agent.status_handler import (
    StatusHandlerError,
    handle_status_not_found,
    handle_status_request,
)
from app.whatsapp_agent.validator import extract_complaint_id, extract_phone_number

logger = get_logger(__name__)


class WhatsAppAgentError(Exception):
    """Raised when WhatsApp agent fails."""


def process_whatsapp_message(message: WhatsAppMessage) -> WhatsAppResponse:
    """
    Main WhatsApp message processing pipeline.
    
    Steps:
    1. Extract phone number
    2. Get conversation state
    3. Classify intent (or use active workflow)
    4. Route to appropriate handler
    5. Generate response
    6. Update conversation state
    """
    phone_number = extract_phone_number(message.From)
    
    logger.info(
        "whatsapp_message_received",
        phone=phone_number,
        has_media=message.NumMedia > 0,
        body_length=len(message.Body),
    )
    
    try:
        # Initialize conversation manager
        conv_manager = ConversationManager(phone_number)
        
        # Check for active workflow
        if conv_manager.has_active_workflow():
            workflow = conv_manager.get_active_workflow()
            logger.info("active_workflow_detected", phone=phone_number, workflow=workflow)
            
            # Route to workflow handler
            if workflow == "housing_assistance":
                response_text = handle_housing_request(phone_number, message.Body)
                conv_manager.add_message("user", message.Body)
                conv_manager.add_message("assistant", response_text)
                return WhatsAppResponse(message=response_text)
        
        # No active workflow - classify intent
        try:
            intent = classify_intent(message.Body)
        except IntentClassificationError as exc:
            logger.warning("intent_classification_failed", error=str(exc))
            intent = create_fallback_intent(message.Body)
        
        # Update language preference
        if intent.language:
            conv_manager.set_language(intent.language)
        
        # Log message with intent
        conv_manager.add_message("user", message.Body, intent.intent)
        
        # Route based on intent
        response_text = route_intent(
            intent=intent.intent,
            message=message,
            phone_number=phone_number,
            conv_manager=conv_manager,
        )
        
        # Log assistant response
        conv_manager.add_message("assistant", response_text)
        
        logger.info(
            "response_sent",
            phone=phone_number,
            intent=intent.intent,
            response_length=len(response_text),
        )
        
        return WhatsAppResponse(message=response_text)
    
    except Exception as exc:
        logger.error("whatsapp_processing_failed", phone=phone_number, error=str(exc))
        
        # Try to get language preference
        try:
            conv_manager = ConversationManager(phone_number)
            language = conv_manager.get_preferred_language()
        except:
            language = "en"
        
        return WhatsAppResponse(message=generate_error_response(language))


def route_intent(
    intent: str,
    message: WhatsAppMessage,
    phone_number: str,
    conv_manager: ConversationManager,
) -> str:
    """Route message to appropriate handler based on intent."""
    language = conv_manager.get_preferred_language()
    
    if intent == "greeting":
        return generate_greeting(language)
    
    elif intent == "complaint_submission":
        return handle_complaint_intent(message, phone_number, language)
    
    elif intent == "complaint_status":
        return handle_status_intent(message, phone_number, language)
    
    elif intent == "housing_help":
        return handle_housing_request(phone_number, message.Body)
    
    elif intent == "escalation_help":
        return handle_escalation_intent(language)
    
    elif intent == "ward_information":
        return handle_ward_info_intent(language)
    
    else:  # unknown
        return generate_unknown_intent_response(language)


def handle_complaint_intent(
    message: WhatsAppMessage,
    phone_number: str,
    language: str,
) -> str:
    """Handle complaint submission intent."""
    # Check if image is attached
    if message.NumMedia > 0 and message.MediaUrl0:
        try:
            acknowledgment = handle_complaint_submission(
                description=message.Body or "Complaint submitted via WhatsApp",
                media_url=message.MediaUrl0,
                phone_number=phone_number,
            )
            
            response = acknowledgment.message
            return generate_bilingual_response(response, language)
        
        except ComplaintHandlerError as exc:
            logger.error("complaint_handling_failed", phone=phone_number, error=str(exc))
            return generate_bilingual_response(
                "Sorry, we couldn't process your complaint. Please try again later.",
                language,
            )
    else:
        # No image attached
        return generate_bilingual_response(
            handle_text_only_complaint(message.Body, phone_number),
            language,
        )


def handle_status_intent(
    message: WhatsAppMessage,
    phone_number: str,
    language: str,
) -> str:
    """Handle complaint status intent."""
    # Extract complaint ID from message
    complaint_id = extract_complaint_id(message.Body)
    
    if not complaint_id:
        return generate_bilingual_response(
            "Please provide your complaint ID.\n\nExample: Track complaint abc123xyz",
            language,
        )
    
    try:
        status_update = handle_status_request(complaint_id)
        return generate_bilingual_response(status_update.message, language)
    
    except StatusHandlerError:
        return generate_bilingual_response(
            handle_status_not_found(complaint_id),
            language,
        )


def handle_escalation_intent(language: str) -> str:
    """Handle escalation help intent."""
    message = (
        "🔔 Escalation Help\n\n"
        "If your complaint hasn't been resolved, you can escalate it.\n\n"
        "To escalate:\n"
        "1. Note your complaint ID\n"
        "2. Call our helpline: 1800-XXX-XXXX\n"
        "3. Or visit your nearest civic office\n\n"
        "Our team will review and escalate your complaint to higher authorities."
    )
    return generate_bilingual_response(message, language)


def handle_ward_info_intent(language: str) -> str:
    """Handle ward information intent."""
    message = (
        "ℹ️ Ward Information\n\n"
        "To get information about your ward:\n"
        "• Ward boundaries\n"
        "• Civic amenities\n"
        "• Infrastructure status\n\n"
        "Please provide your ward number or location, and I'll help you get the information."
    )
    return generate_bilingual_response(message, language)

"""Main bot webhook service."""

from __future__ import annotations

from typing import Optional

from app.bot_webhook.intent_classifier import IntentClassifier
from app.bot_webhook.router import IntentRouter
from app.bot_webhook.schemas import TwilioWebhookPayload, WebhookResponse
from app.bot_webhook.session_manager import SessionManager
from app.bot_webhook.validator import validate_twilio_payload
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class BotWebhookService:
    """Main bot webhook service."""

    def __init__(self):
        """Initialize bot webhook service."""
        self.session_manager = SessionManager()
        self.intent_classifier = IntentClassifier()
        self.router = IntentRouter()

    def process_webhook(self, payload: TwilioWebhookPayload) -> WebhookResponse:
        """
        Process incoming webhook.
        
        Args:
            payload: Twilio webhook payload
        
        Returns:
            WebhookResponse
        """
        try:
            # Validate payload
            if not validate_twilio_payload(payload.model_dump()):
                logger.error("invalid_webhook_payload")
                return WebhookResponse(
                    message="Invalid request",
                    status="error",
                )
            
            phone = payload.From
            message = payload.Body
            has_media = int(payload.NumMedia) > 0
            media_url = payload.MediaUrl0 if has_media else None
            
            logger.info(
                "webhook_received",
                phone=phone,
                message_length=len(message),
                has_media=has_media,
            )
            
            # Get or create session
            session = self.session_manager.get_or_create_session(phone)
            
            # Add message to history
            self.session_manager.update_session(
                phone,
                add_message={
                    "role": "user",
                    "content": message,
                    "timestamp": str(datetime.utcnow()),
                },
            )
            
            # Check if in active workflow
            if session.workflowState:
                # Continue existing workflow
                intent = session.currentIntent or "UNKNOWN"
                logger.info("continuing_workflow", intent=intent, state=session.workflowState)
            else:
                # Classify intent
                classification = self.intent_classifier.classify_intent(
                    message,
                    has_media,
                    session.conversationHistory,
                )
                
                intent = classification.intent
                language = classification.language
                
                # Update session with language
                self.session_manager.update_session(
                    phone,
                    intent=intent,
                    language=language,
                )
                
                # Update session object
                session.preferredLanguage = language
                session.currentIntent = intent
                
                logger.info(
                    "intent_classified",
                    intent=intent,
                    confidence=classification.confidence,
                    language=language,
                )
            
            # Route to handler
            handler_response = self.router.route(
                intent,
                session,
                message,
                media_url,
            )
            
            # Update session with handler response
            if handler_response.nextState:
                self.session_manager.update_session(
                    phone,
                    workflow_state=handler_response.nextState,
                    context_update=handler_response.contextUpdate,
                )
            
            # Add bot response to history
            self.session_manager.update_session(
                phone,
                add_message={
                    "role": "assistant",
                    "content": handler_response.message,
                    "timestamp": str(datetime.utcnow()),
                },
            )
            
            logger.info("webhook_processed", phone=phone, intent=intent)
            
            return WebhookResponse(
                message=handler_response.message,
                status="success",
                intent=intent,
            )
        
        except Exception as exc:
            logger.error("webhook_processing_failed", error=str(exc))
            return WebhookResponse(
                message="Sorry, something went wrong. Please try again.",
                status="error",
            )


from datetime import datetime

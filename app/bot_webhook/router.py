"""Route intents to appropriate handlers."""

from __future__ import annotations

from typing import Optional

from app.bot_webhook.complaint_handler import ComplaintHandler
from app.bot_webhook.document_handler import DocumentHandler
from app.bot_webhook.greeting_handler import GreetingHandler
from app.bot_webhook.housing_handler import HousingHandler
from app.bot_webhook.schemas import BotSession, HandlerResponse
from app.bot_webhook.status_handler import StatusHandler
from app.bot_webhook.unknown_handler import UnknownHandler
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class IntentRouter:
    """Route intents to handlers."""

    def __init__(self):
        """Initialize router."""
        self.complaint_handler = ComplaintHandler()
        self.status_handler = StatusHandler()
        self.housing_handler = HousingHandler()
        self.document_handler = DocumentHandler()
        self.greeting_handler = GreetingHandler()
        self.unknown_handler = UnknownHandler()

    def route(
        self,
        intent: str,
        session: BotSession,
        message: str,
        media_url: Optional[str] = None,
    ) -> HandlerResponse:
        """
        Route intent to appropriate handler.
        
        Args:
            intent: Classified intent
            session: Current session
            message: User message
            media_url: Optional media URL
        
        Returns:
            HandlerResponse
        """
        try:
            logger.info("routing_intent", intent=intent, phone=session.phone)
            
            if intent == "FILE_COMPLAINT":
                return self.complaint_handler.handle(session, message, media_url)
            
            elif intent == "CHECK_STATUS":
                return self.status_handler.handle(session, message)
            
            elif intent == "FIND_HOUSING":
                return self.housing_handler.handle(session, message)
            
            elif intent == "DOCUMENT_UPLOAD":
                return self.document_handler.handle(session, message, media_url)
            
            elif intent == "GREET":
                return self.greeting_handler.handle(session, message)
            
            elif intent == "WARD_INFO":
                # Simple ward info response
                from app.bot_webhook.multilingual_responder import MultilingualResponder
                responder = MultilingualResponder()
                return HandlerResponse(
                    message=responder.get_response("ward_info", session.preferredLanguage)
                )
            
            else:
                return self.unknown_handler.handle(session, message)
        
        except Exception as exc:
            logger.error("routing_failed", intent=intent, error=str(exc))
            return self.unknown_handler.handle(session, message)

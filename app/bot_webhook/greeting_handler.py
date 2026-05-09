"""Handle greeting messages."""

from __future__ import annotations

from app.bot_webhook.multilingual_responder import MultilingualResponder
from app.bot_webhook.schemas import BotSession, HandlerResponse
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class GreetingHandler:
    """Handle greeting messages."""

    def __init__(self):
        """Initialize greeting handler."""
        self.responder = MultilingualResponder()

    def handle(self, session: BotSession, message: str) -> HandlerResponse:
        """Handle greeting."""
        language = session.preferredLanguage
        
        response_msg = self.responder.get_response("greet", language)
        
        logger.info("greeting_sent", phone=session.phone, language=language)
        
        return HandlerResponse(message=response_msg)

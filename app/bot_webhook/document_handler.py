"""Handle document upload workflow."""

from __future__ import annotations

from typing import Optional

from app.bot_webhook.multilingual_responder import MultilingualResponder
from app.bot_webhook.schemas import BotSession, HandlerResponse
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class DocumentHandler:
    """Handle document upload workflow."""

    def __init__(self):
        """Initialize document handler."""
        self.responder = MultilingualResponder()

    def handle(
        self,
        session: BotSession,
        message: str,
        media_url: Optional[str] = None,
    ) -> HandlerResponse:
        """Handle document upload."""
        language = session.preferredLanguage
        
        if media_url:
            # Document received
            response_msg = self.responder.get_response(
                "complaint_filed",
                language,
                complaint_id="DOC-" + session.phone[-6:],
            )
        else:
            # Ask for document
            response_msg = self.responder.get_response(
                "document_upload",
                language,
            )
        
        logger.info("document_handled", phone=session.phone, has_media=bool(media_url))
        
        return HandlerResponse(message=response_msg)

"""Handle complaint filing workflow."""

from __future__ import annotations

from typing import Optional

from app.bot_webhook.multilingual_responder import MultilingualResponder
from app.bot_webhook.schemas import BotSession, HandlerResponse
from app.bot_webhook.session_manager import SessionManager
from app.complaint_classifier.service import ComplaintClassifierService
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ComplaintHandler:
    """Handle complaint filing workflow."""

    def __init__(self):
        """Initialize complaint handler."""
        self.session_manager = SessionManager()
        self.responder = MultilingualResponder()
        self.classifier_service = ComplaintClassifierService()

    def handle(
        self,
        session: BotSession,
        message: str,
        media_url: Optional[str] = None,
    ) -> HandlerResponse:
        """
        Handle complaint filing.
        
        Args:
            session: Current session
            message: User message
            media_url: Optional media URL
        
        Returns:
            HandlerResponse
        """
        try:
            language = session.preferredLanguage
            
            # Check workflow state
            workflow_state = session.workflowState
            
            if not workflow_state:
                # Start complaint workflow
                if media_url:
                    # Has image, can file complaint
                    return self._process_complaint_with_image(
                        session,
                        message,
                        media_url,
                        language,
                    )
                else:
                    # Ask for image
                    response_msg = self.responder.get_response(
                        "complaint_need_image",
                        language,
                    )
                    
                    # Update session
                    self.session_manager.update_session(
                        session.phone,
                        intent="FILE_COMPLAINT",
                        workflow_state="awaiting_image",
                    )
                    
                    return HandlerResponse(
                        message=response_msg,
                        nextState="awaiting_image",
                    )
            
            elif workflow_state == "awaiting_image":
                if media_url:
                    return self._process_complaint_with_image(
                        session,
                        message,
                        media_url,
                        language,
                    )
                else:
                    response_msg = self.responder.get_response(
                        "complaint_still_need_image",
                        language,
                    )
                    return HandlerResponse(message=response_msg)
            
            else:
                # Unknown state, restart
                self.session_manager.clear_workflow(session.phone)
                response_msg = self.responder.get_response(
                    "complaint_start",
                    language,
                )
                return HandlerResponse(message=response_msg)
        
        except Exception as exc:
            logger.error("complaint_handler_failed", error=str(exc))
            return HandlerResponse(
                message=self.responder.get_response("error", session.preferredLanguage),
                success=False,
            )

    def _process_complaint_with_image(
        self,
        session: BotSession,
        description: str,
        media_url: str,
        language: str,
    ) -> HandlerResponse:
        """Process complaint with image."""
        try:
            # For now, acknowledge receipt
            # In production, would invoke complaint_classifier
            
            complaint_id = f"CMP-{session.phone[-6:]}-{int(datetime.utcnow().timestamp())}"
            
            response_msg = self.responder.get_response(
                "complaint_filed",
                language,
                complaint_id=complaint_id,
            )
            
            # Clear workflow
            self.session_manager.clear_workflow(session.phone)
            
            # Store complaint ID in context
            self.session_manager.update_session(
                session.phone,
                context_update={"last_complaint_id": complaint_id},
            )
            
            logger.info("complaint_filed", phone=session.phone, complaint_id=complaint_id)
            
            return HandlerResponse(
                message=response_msg,
                contextUpdate={"complaint_id": complaint_id},
            )
        
        except Exception as exc:
            logger.error("complaint_processing_failed", error=str(exc))
            return HandlerResponse(
                message=self.responder.get_response("error", language),
                success=False,
            )


from datetime import datetime

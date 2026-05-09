"""Handle complaint status checking."""

from __future__ import annotations

import re

from app.bot_webhook.multilingual_responder import MultilingualResponder
from app.bot_webhook.schemas import BotSession, HandlerResponse
from app.bot_webhook.session_manager import SessionManager
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class StatusHandler:
    """Handle complaint status checking."""

    def __init__(self):
        """Initialize status handler."""
        self.session_manager = SessionManager()
        self.responder = MultilingualResponder()
        self.db = db

    def handle(
        self,
        session: BotSession,
        message: str,
    ) -> HandlerResponse:
        """
        Handle status check.
        
        Args:
            session: Current session
            message: User message
        
        Returns:
            HandlerResponse
        """
        try:
            language = session.preferredLanguage
            
            # Extract complaint ID from message
            complaint_id = self._extract_complaint_id(message)
            
            if not complaint_id:
                # Check if user has recent complaint
                last_complaint = self.session_manager.get_context(
                    session.phone,
                    "last_complaint_id",
                )
                
                if last_complaint:
                    complaint_id = last_complaint
                else:
                    # Ask for complaint ID
                    response_msg = self.responder.get_response(
                        "status_need_id",
                        language,
                    )
                    return HandlerResponse(message=response_msg)
            
            # Fetch complaint status
            status_info = self._get_complaint_status(complaint_id)
            
            if not status_info:
                response_msg = self.responder.get_response(
                    "status_not_found",
                    language,
                    complaint_id=complaint_id,
                )
                return HandlerResponse(message=response_msg, success=False)
            
            # Generate status response
            response_msg = self.responder.get_response(
                "status_found",
                language,
                complaint_id=complaint_id,
                status=status_info.get("status", "pending"),
                category=status_info.get("category", "unknown"),
            )
            
            logger.info("status_checked", phone=session.phone, complaint_id=complaint_id)
            
            return HandlerResponse(message=response_msg)
        
        except Exception as exc:
            logger.error("status_handler_failed", error=str(exc))
            return HandlerResponse(
                message=self.responder.get_response("error", session.preferredLanguage),
                success=False,
            )

    def _extract_complaint_id(self, message: str) -> str | None:
        """Extract complaint ID from message."""
        # Look for patterns like CMP-123456 or just numbers
        patterns = [
            r"CMP-\d+-\d+",
            r"CMP\d+",
            r"\b\d{6,}\b",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None

    def _get_complaint_status(self, complaint_id: str) -> dict | None:
        """Get complaint status from Firestore."""
        try:
            # Query complaints collection
            complaints_ref = self.db.collection("complaints")
            
            # Try exact match first
            query = complaints_ref.where("complaintId", "==", complaint_id).limit(1)
            docs = list(query.stream())
            
            if docs:
                return docs[0].to_dict()
            
            # Try partial match
            for doc in complaints_ref.limit(100).stream():
                doc_data = doc.to_dict()
                doc_id = doc_data.get("complaintId", "")
                if complaint_id in doc_id or doc_id in complaint_id:
                    return doc_data
            
            return None
        
        except Exception as exc:
            logger.error("status_fetch_failed", error=str(exc))
            return None

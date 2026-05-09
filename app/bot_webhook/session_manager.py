"""Session management for bot conversations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from firebase_admin import firestore

from app.bot_webhook.schemas import BotSession
from app.bot_webhook.validator import sanitize_phone_number
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manage bot conversation sessions."""

    def __init__(self):
        """Initialize session manager."""
        self.db = db
        self.collection = "bot_sessions"

    def get_or_create_session(self, phone: str) -> BotSession:
        """
        Get existing session or create new one.
        
        Args:
            phone: User phone number
        
        Returns:
            BotSession
        """
        try:
            # Sanitize phone
            phone_clean = sanitize_phone_number(phone)
            
            # Try to get existing session
            session_ref = self.db.collection(self.collection).document(phone_clean)
            session_doc = session_ref.get()
            
            if session_doc.exists:
                session_data = session_doc.to_dict()
                
                # Update last updated
                session_ref.update({"lastUpdated": firestore.SERVER_TIMESTAMP})
                
                logger.info("session_loaded", phone=phone_clean)
                
                return BotSession(**session_data)
            else:
                # Create new session
                new_session = BotSession(phone=phone_clean)
                
                session_ref.set(new_session.model_dump())
                
                logger.info("session_created", phone=phone_clean)
                
                return new_session
        
        except Exception as exc:
            logger.error("session_load_failed", phone=phone, error=str(exc))
            # Return default session
            return BotSession(phone=sanitize_phone_number(phone))

    def update_session(
        self,
        phone: str,
        intent: Optional[str] = None,
        workflow_state: Optional[str] = None,
        language: Optional[str] = None,
        context_update: Optional[dict[str, Any]] = None,
        add_message: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Update session data.
        
        Args:
            phone: User phone number
            intent: Current intent
            workflow_state: Current workflow state
            language: Preferred language
            context_update: Context data to update
            add_message: Message to add to history
        """
        try:
            phone_clean = sanitize_phone_number(phone)
            session_ref = self.db.collection(self.collection).document(phone_clean)
            
            update_data = {"lastUpdated": firestore.SERVER_TIMESTAMP}
            
            if intent:
                update_data["currentIntent"] = intent
            
            if workflow_state:
                update_data["workflowState"] = workflow_state
            
            if language:
                update_data["preferredLanguage"] = language
            
            if context_update:
                # Merge context data
                session_doc = session_ref.get()
                if session_doc.exists:
                    existing_context = session_doc.to_dict().get("contextData", {})
                    existing_context.update(context_update)
                    update_data["contextData"] = existing_context
                else:
                    update_data["contextData"] = context_update
            
            if add_message:
                # Add to conversation history
                session_doc = session_ref.get()
                if session_doc.exists:
                    history = session_doc.to_dict().get("conversationHistory", [])
                    history.append(add_message)
                    # Keep last 20 messages
                    update_data["conversationHistory"] = history[-20:]
                else:
                    update_data["conversationHistory"] = [add_message]
            
            session_ref.update(update_data)
            
            logger.info("session_updated", phone=phone_clean, intent=intent)
        
        except Exception as exc:
            logger.error("session_update_failed", phone=phone, error=str(exc))

    def clear_workflow(self, phone: str) -> None:
        """Clear workflow state."""
        try:
            phone_clean = sanitize_phone_number(phone)
            session_ref = self.db.collection(self.collection).document(phone_clean)
            
            session_ref.update({
                "currentIntent": None,
                "workflowState": None,
                "contextData": {},
                "lastUpdated": firestore.SERVER_TIMESTAMP,
            })
            
            logger.info("workflow_cleared", phone=phone_clean)
        
        except Exception as exc:
            logger.error("workflow_clear_failed", phone=phone, error=str(exc))

    def get_context(self, phone: str, key: str) -> Any:
        """Get context value from session."""
        try:
            phone_clean = sanitize_phone_number(phone)
            session_ref = self.db.collection(self.collection).document(phone_clean)
            session_doc = session_ref.get()
            
            if session_doc.exists:
                context = session_doc.to_dict().get("contextData", {})
                return context.get(key)
            
            return None
        
        except Exception as exc:
            logger.error("context_get_failed", phone=phone, error=str(exc))
            return None

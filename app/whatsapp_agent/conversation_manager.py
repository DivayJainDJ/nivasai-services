"""Conversation state management using Firestore."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from firebase_admin import firestore

from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger
from app.whatsapp_agent.schemas import ConversationState

logger = get_logger(__name__)

COLLECTION_NAME = "whatsapp_conversations"


class ConversationManager:
    """Manage conversation state for WhatsApp users."""

    def __init__(self, phone_number: str):
        """Initialize conversation manager for a phone number."""
        self.phone_number = phone_number
        self.db = get_firestore_client()

    def get_state(self) -> ConversationState:
        """Get current conversation state."""
        doc = self.db.collection(COLLECTION_NAME).document(self.phone_number).get()
        
        if doc.exists:
            data = doc.to_dict() or {}
            return ConversationState(
                phoneNumber=self.phone_number,
                lastIntent=data.get("lastIntent"),
                activeWorkflow=data.get("activeWorkflow"),
                workflowData=data.get("workflowData", {}),
                preferredLanguage=data.get("preferredLanguage", "en"),
                conversationHistory=data.get("conversationHistory", []),
                lastMessageAt=data.get("lastMessageAt"),
                createdAt=data.get("createdAt"),
            )
        else:
            # Create new state
            return ConversationState(
                phoneNumber=self.phone_number,
                createdAt=datetime.now(timezone.utc),
            )

    def save_state(self, state: ConversationState) -> None:
        """Save conversation state to Firestore."""
        doc_ref = self.db.collection(COLLECTION_NAME).document(self.phone_number)
        
        data = {
            "phoneNumber": state.phoneNumber,
            "lastIntent": state.lastIntent,
            "activeWorkflow": state.activeWorkflow,
            "workflowData": state.workflowData,
            "preferredLanguage": state.preferredLanguage,
            "conversationHistory": state.conversationHistory[-20:],  # Keep last 20 messages
            "lastMessageAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        
        if state.createdAt:
            data["createdAt"] = state.createdAt
        else:
            data["createdAt"] = firestore.SERVER_TIMESTAMP
        
        doc_ref.set(data, merge=True)
        
        logger.info(
            "conversation_state_saved",
            phone=self.phone_number,
            workflow=state.activeWorkflow,
        )

    def add_message(self, role: str, content: str, intent: Optional[str] = None) -> None:
        """Add message to conversation history."""
        state = self.get_state()
        
        message = {
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if intent:
            message["intent"] = intent
        
        state.conversationHistory.append(message)
        
        if intent:
            state.lastIntent = intent
        
        self.save_state(state)

    def start_workflow(self, workflow_name: str, initial_data: dict = None) -> None:
        """Start a new workflow."""
        state = self.get_state()
        state.activeWorkflow = workflow_name
        state.workflowData = initial_data or {}
        self.save_state(state)
        
        logger.info("workflow_started", phone=self.phone_number, workflow=workflow_name)

    def update_workflow_data(self, data: dict) -> None:
        """Update workflow data."""
        state = self.get_state()
        state.workflowData.update(data)
        self.save_state(state)

    def complete_workflow(self) -> None:
        """Complete and clear active workflow."""
        state = self.get_state()
        
        logger.info(
            "workflow_completed",
            phone=self.phone_number,
            workflow=state.activeWorkflow,
        )
        
        state.activeWorkflow = None
        state.workflowData = {}
        self.save_state(state)

    def set_language(self, language: str) -> None:
        """Set preferred language."""
        state = self.get_state()
        state.preferredLanguage = language
        self.save_state(state)

    def get_workflow_data(self) -> dict:
        """Get current workflow data."""
        state = self.get_state()
        return state.workflowData

    def has_active_workflow(self) -> bool:
        """Check if user has an active workflow."""
        state = self.get_state()
        return state.activeWorkflow is not None

    def get_active_workflow(self) -> Optional[str]:
        """Get active workflow name."""
        state = self.get_state()
        return state.activeWorkflow

    def get_preferred_language(self) -> str:
        """Get user's preferred language."""
        state = self.get_state()
        return state.preferredLanguage

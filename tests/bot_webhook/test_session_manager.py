"""Test session manager."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.bot_webhook.session_manager import SessionManager
from app.bot_webhook.schemas import BotSession


@pytest.fixture
def session_manager():
    """Create session manager."""
    return SessionManager()


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    with patch('app.bot_webhook.session_manager.get_firestore_client') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


class TestSessionManager:
    """Test session manager."""
    
    def test_create_new_session(self, session_manager, mock_firestore):
        """Test creating new session."""
        phone = "+919999999999"
        
        # Mock Firestore get returning None (no existing session)
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        session = session_manager.get_or_create_session(phone)
        
        assert session.phone == phone
        assert session.currentIntent is None
        assert session.workflowState is None
        assert session.preferredLanguage == "en"
        assert session.conversationHistory == []
        assert session.context == {}
    
    def test_get_existing_session(self, session_manager, mock_firestore):
        """Test getting existing session."""
        phone = "+919999999999"
        
        # Mock Firestore get returning existing session
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "phone": phone,
            "currentIntent": "FILE_COMPLAINT",
            "workflowState": "collecting_details",
            "preferredLanguage": "hi",
            "conversationHistory": [
                {"role": "user", "content": "Hello"}
            ],
            "context": {"complaint_type": "garbage"},
            "lastUpdated": datetime.utcnow(),
        }
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        session = session_manager.get_or_create_session(phone)
        
        assert session.phone == phone
        assert session.currentIntent == "FILE_COMPLAINT"
        assert session.workflowState == "collecting_details"
        assert session.preferredLanguage == "hi"
        assert len(session.conversationHistory) == 1
        assert session.context["complaint_type"] == "garbage"
    
    def test_update_session_intent(self, session_manager, mock_firestore):
        """Test updating session intent."""
        phone = "+919999999999"
        
        session_manager.update_session(
            phone,
            intent="CHECK_STATUS",
            language="en",
        )
        
        # Verify Firestore update was called
        mock_firestore.collection.return_value.document.return_value.set.assert_called_once()
        call_args = mock_firestore.collection.return_value.document.return_value.set.call_args
        assert call_args[1]["merge"] is True
        assert "currentIntent" in call_args[0][0]
        assert call_args[0][0]["currentIntent"] == "CHECK_STATUS"
    
    def test_update_session_workflow_state(self, session_manager, mock_firestore):
        """Test updating workflow state."""
        phone = "+919999999999"
        
        session_manager.update_session(
            phone,
            workflow_state="collecting_income",
        )
        
        # Verify Firestore update was called
        mock_firestore.collection.return_value.document.return_value.set.assert_called_once()
        call_args = mock_firestore.collection.return_value.document.return_value.set.call_args
        assert "workflowState" in call_args[0][0]
        assert call_args[0][0]["workflowState"] == "collecting_income"
    
    def test_update_session_context(self, session_manager, mock_firestore):
        """Test updating session context."""
        phone = "+919999999999"
        
        session_manager.update_session(
            phone,
            context_update={"income": 25000, "family_size": 4},
        )
        
        # Verify Firestore update was called
        mock_firestore.collection.return_value.document.return_value.set.assert_called_once()
        call_args = mock_firestore.collection.return_value.document.return_value.set.call_args
        assert "context" in call_args[0][0]
    
    def test_add_message_to_history(self, session_manager, mock_firestore):
        """Test adding message to conversation history."""
        phone = "+919999999999"
        
        message = {
            "role": "user",
            "content": "Hello",
            "timestamp": str(datetime.utcnow()),
        }
        
        session_manager.update_session(
            phone,
            add_message=message,
        )
        
        # Verify Firestore update was called with ArrayUnion
        mock_firestore.collection.return_value.document.return_value.set.assert_called_once()
    
    def test_clear_workflow_state(self, session_manager, mock_firestore):
        """Test clearing workflow state."""
        phone = "+919999999999"
        
        session_manager.update_session(
            phone,
            workflow_state=None,
        )
        
        # Verify Firestore update was called
        mock_firestore.collection.return_value.document.return_value.set.assert_called_once()
        call_args = mock_firestore.collection.return_value.document.return_value.set.call_args
        assert call_args[0][0]["workflowState"] is None
    
    def test_session_with_multiple_messages(self, session_manager, mock_firestore):
        """Test session with multiple messages in history."""
        phone = "+919999999999"
        
        # Mock existing session with history
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "phone": phone,
            "currentIntent": "FILE_COMPLAINT",
            "workflowState": None,
            "preferredLanguage": "en",
            "conversationHistory": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help?"},
                {"role": "user", "content": "I want to file a complaint"},
            ],
            "context": {},
            "lastUpdated": datetime.utcnow(),
        }
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        session = session_manager.get_or_create_session(phone)
        
        assert len(session.conversationHistory) == 3
        assert session.conversationHistory[0]["role"] == "user"
        assert session.conversationHistory[1]["role"] == "assistant"
    
    def test_firestore_failure_fallback(self, session_manager, mock_firestore):
        """Test fallback when Firestore fails."""
        phone = "+919999999999"
        
        # Mock Firestore failure
        mock_firestore.collection.return_value.document.return_value.get.side_effect = Exception("Firestore error")
        
        session = session_manager.get_or_create_session(phone)
        
        # Should return default session
        assert session.phone == phone
        assert session.currentIntent is None
        assert session.conversationHistory == []

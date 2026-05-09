"""Test bot webhook service."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.bot_webhook.service import BotWebhookService
from app.bot_webhook.schemas import (
    BotSession,
    HandlerResponse,
    IntentClassification,
    TwilioWebhookPayload,
)


@pytest.fixture
def service():
    """Create bot webhook service."""
    return BotWebhookService()


@pytest.fixture
def mock_session():
    """Mock bot session."""
    return BotSession(
        phone="+919999999999",
        currentIntent=None,
        workflowState=None,
        preferredLanguage="en",
        conversationHistory=[],
        context={},
        lastUpdated=datetime.utcnow(),
    )


@pytest.fixture
def mock_classification():
    """Mock intent classification."""
    return IntentClassification(
        intent="FILE_COMPLAINT",
        confidence=0.95,
        language="en",
        entities={},
    )


class TestBotWebhookService:
    """Test bot webhook service."""
    
    def test_process_complaint_webhook(self, service, mock_session, mock_classification):
        """Test processing complaint webhook."""
        payload = TwilioWebhookPayload(
            Body="There is garbage on my street",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="0",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', return_value=mock_session), \
             patch.object(service.session_manager, 'update_session'), \
             patch.object(service.intent_classifier, 'classify_intent', return_value=mock_classification), \
             patch.object(service.router, 'route', return_value=HandlerResponse(
                 message="Thank you for reporting. Your complaint has been registered.",
                 nextState=None,
             )):
            
            response = service.process_webhook(payload)
            
            assert response.status == "success"
            assert response.intent == "FILE_COMPLAINT"
            assert "complaint" in response.message.lower() or "registered" in response.message.lower()
    
    def test_process_status_webhook(self, service, mock_session, mock_classification):
        """Test processing status check webhook."""
        mock_classification.intent = "CHECK_STATUS"
        
        payload = TwilioWebhookPayload(
            Body="What is the status of C12345",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="0",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', return_value=mock_session), \
             patch.object(service.session_manager, 'update_session'), \
             patch.object(service.intent_classifier, 'classify_intent', return_value=mock_classification), \
             patch.object(service.router, 'route', return_value=HandlerResponse(
                 message="Your complaint C12345 is in progress.",
                 nextState=None,
             )):
            
            response = service.process_webhook(payload)
            
            assert response.status == "success"
            assert response.intent == "CHECK_STATUS"
    
    def test_process_housing_webhook(self, service, mock_session, mock_classification):
        """Test processing housing request webhook."""
        mock_classification.intent = "FIND_HOUSING"
        
        payload = TwilioWebhookPayload(
            Body="I need affordable housing",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="0",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', return_value=mock_session), \
             patch.object(service.session_manager, 'update_session'), \
             patch.object(service.intent_classifier, 'classify_intent', return_value=mock_classification), \
             patch.object(service.router, 'route', return_value=HandlerResponse(
                 message="I can help you find housing. What is your monthly income?",
                 nextState="collecting_income",
             )):
            
            response = service.process_webhook(payload)
            
            assert response.status == "success"
            assert response.intent == "FIND_HOUSING"
    
    def test_process_webhook_with_media(self, service, mock_session, mock_classification):
        """Test processing webhook with media attachment."""
        mock_classification.intent = "DOCUMENT_UPLOAD"
        
        payload = TwilioWebhookPayload(
            Body="Here is my Aadhaar card",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="1",
            MediaUrl0="https://api.twilio.com/media/ME123",
            MediaContentType0="image/jpeg",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', return_value=mock_session), \
             patch.object(service.session_manager, 'update_session'), \
             patch.object(service.intent_classifier, 'classify_intent', return_value=mock_classification), \
             patch.object(service.router, 'route', return_value=HandlerResponse(
                 message="Document received. Processing...",
                 nextState=None,
             )):
            
            response = service.process_webhook(payload)
            
            assert response.status == "success"
            assert response.intent == "DOCUMENT_UPLOAD"
    
    def test_process_greeting_webhook(self, service, mock_session, mock_classification):
        """Test processing greeting webhook."""
        mock_classification.intent = "GREET"
        
        payload = TwilioWebhookPayload(
            Body="Hello",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="0",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', return_value=mock_session), \
             patch.object(service.session_manager, 'update_session'), \
             patch.object(service.intent_classifier, 'classify_intent', return_value=mock_classification), \
             patch.object(service.router, 'route', return_value=HandlerResponse(
                 message="Hello! Welcome to NivasAI. How can I help you today?",
                 nextState=None,
             )):
            
            response = service.process_webhook(payload)
            
            assert response.status == "success"
            assert response.intent == "GREET"
    
    def test_continue_existing_workflow(self, service, mock_classification):
        """Test continuing existing workflow."""
        # Session with active workflow
        active_session = BotSession(
            phone="+919999999999",
            currentIntent="FIND_HOUSING",
            workflowState="collecting_income",
            preferredLanguage="en",
            conversationHistory=[
                {"role": "user", "content": "I need housing"},
                {"role": "assistant", "content": "What is your income?"},
            ],
            context={},
            lastUpdated=datetime.utcnow(),
        )
        
        payload = TwilioWebhookPayload(
            Body="25000 per month",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="0",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', return_value=active_session), \
             patch.object(service.session_manager, 'update_session'), \
             patch.object(service.router, 'route', return_value=HandlerResponse(
                 message="Thank you. How many family members?",
                 nextState="collecting_family_size",
             )):
            
            response = service.process_webhook(payload)
            
            assert response.status == "success"
            # Should continue with FIND_HOUSING, not reclassify
            assert response.intent == "FIND_HOUSING"
    
    def test_process_hindi_webhook(self, service, mock_session, mock_classification):
        """Test processing Hindi webhook."""
        mock_classification.language = "hi"
        
        payload = TwilioWebhookPayload(
            Body="मेरी सड़क पर कचरा है",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="0",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', return_value=mock_session), \
             patch.object(service.session_manager, 'update_session'), \
             patch.object(service.intent_classifier, 'classify_intent', return_value=mock_classification), \
             patch.object(service.router, 'route', return_value=HandlerResponse(
                 message="शिकायत दर्ज की गई है।",
                 nextState=None,
             )):
            
            response = service.process_webhook(payload)
            
            assert response.status == "success"
    
    def test_invalid_payload(self, service):
        """Test handling invalid payload."""
        payload = TwilioWebhookPayload(
            Body="",
            From="",  # Invalid: empty phone
            To="",
            MessageSid="",
            NumMedia="0",
        )
        
        response = service.process_webhook(payload)
        
        assert response.status == "error"
        assert "invalid" in response.message.lower()
    
    def test_service_exception_handling(self, service, mock_session):
        """Test service exception handling."""
        payload = TwilioWebhookPayload(
            Body="Test message",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="0",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', side_effect=Exception("Database error")):
            response = service.process_webhook(payload)
            
            assert response.status == "error"
            assert "wrong" in response.message.lower()
    
    def test_conversation_history_updated(self, service, mock_session, mock_classification):
        """Test that conversation history is updated."""
        payload = TwilioWebhookPayload(
            Body="Hello",
            From="whatsapp:+919999999999",
            To="whatsapp:+911234567890",
            MessageSid="SM123",
            NumMedia="0",
        )
        
        with patch.object(service.session_manager, 'get_or_create_session', return_value=mock_session), \
             patch.object(service.session_manager, 'update_session') as mock_update, \
             patch.object(service.intent_classifier, 'classify_intent', return_value=mock_classification), \
             patch.object(service.router, 'route', return_value=HandlerResponse(
                 message="Hi there!",
                 nextState=None,
             )):
            
            service.process_webhook(payload)
            
            # Verify update_session was called multiple times
            assert mock_update.call_count >= 2

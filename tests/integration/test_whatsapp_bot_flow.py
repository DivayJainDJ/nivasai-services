"""Test complete WhatsApp bot flow end-to-end."""

import pytest
from unittest.mock import MagicMock, patch


class TestWhatsAppBotFlow:
    """Test complete WhatsApp bot workflow."""
    
    def test_bot_webhook_complaint_flow(
        self,
        client,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
        sample_twilio_payload,
    ):
        """Test bot webhook complaint filing flow."""
        # Mock session
        mock_session_doc = MagicMock()
        mock_session_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_session_doc
        
        # Mock intent classification
        intent_response = mock_gemini_response(
            '{"intent": "FILE_COMPLAINT", "confidence": 0.95, "language": "en", "entities": {}}'
        )
        
        # Mock complaint classification
        complaint_response = mock_gemini_response(
            '{"category": "Waste Management", "severity": "medium", "department": "Sanitation", "priority": 2}'
        )
        
        with patch('app.bot_webhook.intent_classifier.get_gemini_client') as mock_intent_client, \
             patch('app.complaint_classifier.classifier.get_gemini_client') as mock_complaint_client:
            
            mock_intent_model = MagicMock()
            mock_intent_model.generate_content.return_value = intent_response
            mock_intent_client.return_value.GenerativeModel.return_value = mock_intent_model
            
            mock_complaint_model = MagicMock()
            mock_complaint_model.generate_content.return_value = complaint_response
            mock_complaint_client.return_value.GenerativeModel.return_value = mock_complaint_model
            
            # Send webhook
            response = client.post(
                "/api/bot/webhook",
                data=sample_twilio_payload
            )
            
            assert response.status_code == 200
            response_text = response.text
            assert len(response_text) > 0
    
    def test_bot_webhook_housing_flow(
        self,
        client,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
    ):
        """Test bot webhook housing search flow."""
        # Mock session with housing workflow
        mock_session_doc = MagicMock()
        mock_session_doc.exists = True
        mock_session_doc.to_dict.return_value = {
            "phone": "+919876543210",
            "currentIntent": "FIND_HOUSING",
            "workflowState": "collecting_income",
            "preferredLanguage": "en",
            "conversationHistory": [],
            "context": {},
        }
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_session_doc
        
        # Mock intent classification
        intent_response = mock_gemini_response(
            '{"intent": "FIND_HOUSING", "confidence": 0.96, "language": "en", "entities": {}}'
        )
        
        with patch('app.bot_webhook.intent_classifier.get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = intent_response
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            # Send income response
            response = client.post(
                "/api/bot/webhook",
                data={
                    "Body": "25000",
                    "From": "whatsapp:+919876543210",
                    "To": "whatsapp:+14155238886",
                    "MessageSid": "SM123456",
                    "NumMedia": "0",
                }
            )
            
            assert response.status_code == 200
            response_text = response.text
            assert len(response_text) > 0
    
    def test_intent_classification_accuracy(
        self,
        mock_gemini,
        mock_gemini_response,
    ):
        """Test intent classification for different message types."""
        from app.bot_webhook.intent_classifier import IntentClassifier
        
        classifier = IntentClassifier()
        
        test_cases = [
            ("There is garbage on my street", "FILE_COMPLAINT"),
            ("What is the status of C12345", "CHECK_STATUS"),
            ("I need affordable housing", "FIND_HOUSING"),
            ("Here is my Aadhaar card", "DOCUMENT_UPLOAD"),
            ("Hello", "GREET"),
        ]
        
        for message, expected_intent in test_cases:
            intent_response = mock_gemini_response(
                f'{{"intent": "{expected_intent}", "confidence": 0.95, "language": "en", "entities": {{}}}}'
            )
            
            with patch('app.bot_webhook.intent_classifier.get_gemini_client') as mock_client:
                mock_model = MagicMock()
                mock_model.generate_content.return_value = intent_response
                mock_client.return_value.GenerativeModel.return_value = mock_model
                
                result = classifier.classify_intent(message, False, [])
                
                assert result.intent == expected_intent
                assert result.confidence > 0.9
    
    def test_session_persistence(
        self,
        mock_firestore,
    ):
        """Test session persistence across messages."""
        from app.bot_webhook.session_manager import SessionManager
        
        manager = SessionManager()
        
        # Mock Firestore
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Create new session
        session = manager.get_or_create_session("+919876543210")
        
        assert session.phone == "+919876543210"
        assert session.currentIntent is None
        assert session.conversationHistory == []
        
        # Update session
        manager.update_session(
            "+919876543210",
            intent="FIND_HOUSING",
            workflow_state="collecting_income",
        )
        
        # Verify Firestore set was called
        mock_firestore.collection.return_value.document.return_value.set.assert_called()

"""Test intent classifier."""

import pytest
from unittest.mock import MagicMock, patch

from app.bot_webhook.intent_classifier import IntentClassifier
from app.bot_webhook.schemas import IntentClassification


@pytest.fixture
def classifier():
    """Create intent classifier."""
    return IntentClassifier()


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini response."""
    def _mock(intent: str, confidence: float = 0.95, language: str = "en"):
        mock_response = MagicMock()
        mock_response.text = f'{{"intent": "{intent}", "confidence": {confidence}, "language": "{language}", "entities": {{}}}}'
        return mock_response
    return _mock


class TestIntentClassifier:
    """Test intent classifier."""
    
    def test_classify_complaint_intent(self, classifier, mock_gemini_response):
        """Test complaint intent classification."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("FILE_COMPLAINT")
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            result = classifier.classify_intent(
                "There is garbage on my street",
                has_media=False,
                conversation_history=[],
            )
            
            assert result.intent == "FILE_COMPLAINT"
            assert result.confidence > 0.9
            assert result.language in ["en", "hi"]
    
    def test_classify_status_intent(self, classifier, mock_gemini_response):
        """Test status check intent classification."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("CHECK_STATUS")
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            result = classifier.classify_intent(
                "What is the status of complaint C12345",
                has_media=False,
                conversation_history=[],
            )
            
            assert result.intent == "CHECK_STATUS"
            assert result.confidence > 0.9
    
    def test_classify_housing_intent(self, classifier, mock_gemini_response):
        """Test housing intent classification."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("FIND_HOUSING")
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            result = classifier.classify_intent(
                "I need affordable housing",
                has_media=False,
                conversation_history=[],
            )
            
            assert result.intent == "FIND_HOUSING"
            assert result.confidence > 0.9
    
    def test_classify_document_intent(self, classifier, mock_gemini_response):
        """Test document upload intent classification."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("DOCUMENT_UPLOAD")
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            result = classifier.classify_intent(
                "Here is my Aadhaar card",
                has_media=True,
                conversation_history=[],
            )
            
            assert result.intent == "DOCUMENT_UPLOAD"
            assert result.confidence > 0.9
    
    def test_classify_greeting_intent(self, classifier, mock_gemini_response):
        """Test greeting intent classification."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("GREET")
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            result = classifier.classify_intent(
                "Hello",
                has_media=False,
                conversation_history=[],
            )
            
            assert result.intent == "GREET"
            assert result.confidence > 0.9
    
    def test_classify_hindi_message(self, classifier, mock_gemini_response):
        """Test Hindi message classification."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("FILE_COMPLAINT", language="hi")
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            result = classifier.classify_intent(
                "मेरी सड़क पर कचरा है",
                has_media=False,
                conversation_history=[],
            )
            
            assert result.intent == "FILE_COMPLAINT"
            assert result.language == "hi"
    
    def test_classify_with_conversation_history(self, classifier, mock_gemini_response):
        """Test classification with conversation history."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("CHECK_STATUS")
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            history = [
                {"role": "user", "content": "I filed a complaint yesterday"},
                {"role": "assistant", "content": "Your complaint ID is C12345"},
            ]
            
            result = classifier.classify_intent(
                "What's the status?",
                has_media=False,
                conversation_history=history,
            )
            
            assert result.intent == "CHECK_STATUS"
    
    def test_classify_unknown_intent(self, classifier, mock_gemini_response):
        """Test unknown intent classification."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("UNKNOWN", confidence=0.3)
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            result = classifier.classify_intent(
                "asdfghjkl",
                has_media=False,
                conversation_history=[],
            )
            
            assert result.intent == "UNKNOWN"
    
    def test_classify_with_media(self, classifier, mock_gemini_response):
        """Test classification with media attachment."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_gemini_response("FILE_COMPLAINT")
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            result = classifier.classify_intent(
                "Look at this problem",
                has_media=True,
                conversation_history=[],
            )
            
            assert result.intent in ["FILE_COMPLAINT", "DOCUMENT_UPLOAD"]
    
    def test_gemini_failure_fallback(self, classifier):
        """Test fallback when Gemini fails."""
        with patch.object(classifier, '_get_gemini_client') as mock_client:
            mock_client.side_effect = Exception("Gemini API error")
            
            result = classifier.classify_intent(
                "Test message",
                has_media=False,
                conversation_history=[],
            )
            
            assert result.intent == "UNKNOWN"
            assert result.confidence == 0.0

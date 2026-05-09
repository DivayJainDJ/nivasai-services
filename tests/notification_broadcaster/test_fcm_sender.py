"""Test FCM sender."""

import pytest
from unittest.mock import MagicMock, patch

from app.notification_broadcaster.fcm_sender import FCMSender
from app.notification_broadcaster.schemas import NotificationPayload


@pytest.fixture
def sender():
    """Create FCM sender."""
    return FCMSender()


@pytest.fixture
def sample_payload():
    """Sample notification payload."""
    return NotificationPayload(
        title="Test Notification",
        body="This is a test notification",
        type="test",
        priority="high",
        targetRoles=["officer"],
        data={"key": "value"},
    )


@pytest.fixture
def sample_tokens():
    """Sample FCM tokens."""
    return [
        "token1_abc123def456ghi789",
        "token2_jkl012mno345pqr678",
        "token3_stu901vwx234yz567",
    ]


class TestFCMSender:
    """Test FCM sender."""
    
    def test_build_fcm_message(self, sender, sample_payload):
        """Test building FCM message."""
        message = sender._build_fcm_message(sample_payload)
        
        assert message["notification"]["title"] == "Test Notification"
        assert message["notification"]["body"] == "This is a test notification"
        assert message["data"]["type"] == "test"
        assert message["data"]["priority"] == "high"
        assert message["android"]["priority"] == "high"
    
    def test_build_fcm_message_normal_priority(self, sender):
        """Test building FCM message with normal priority."""
        payload = NotificationPayload(
            title="Normal Priority",
            body="Normal notification",
            type="test",
            priority="normal",
        )
        
        message = sender._build_fcm_message(payload)
        
        assert message["android"]["priority"] == "normal"
        assert message["apns"]["headers"]["apns-priority"] == "5"
    
    @patch('app.notification_broadcaster.fcm_sender.messaging.send_multicast')
    def test_send_notification_success(self, mock_send, sender, sample_payload, sample_tokens):
        """Test successful notification send."""
        # Mock FCM response
        mock_response = MagicMock()
        mock_response.success_count = 3
        mock_response.failure_count = 0
        mock_response.responses = [
            MagicMock(success=True) for _ in sample_tokens
        ]
        mock_send.return_value = mock_response
        
        result = sender.send_notification(sample_tokens, sample_payload)
        
        assert result.successCount == 3
        assert result.failureCount == 0
        assert len(result.invalidTokens) == 0
    
    @patch('app.notification_broadcaster.fcm_sender.messaging.send_multicast')
    def test_send_notification_with_failures(self, mock_send, sender, sample_payload, sample_tokens):
        """Test notification send with failures."""
        # Mock FCM response with failures
        mock_response = MagicMock()
        mock_response.success_count = 2
        mock_response.failure_count = 1
        
        # Create mock responses
        responses = [
            MagicMock(success=True),
            MagicMock(success=True),
            MagicMock(success=False, exception=MagicMock(code="invalid-registration-token")),
        ]
        mock_response.responses = responses
        mock_send.return_value = mock_response
        
        result = sender.send_notification(sample_tokens, sample_payload)
        
        assert result.successCount == 2
        assert result.failureCount == 1
        assert len(result.invalidTokens) == 1
    
    @patch('app.notification_broadcaster.fcm_sender.messaging.send_multicast')
    def test_send_notification_batch_chunking(self, mock_send, sender, sample_payload):
        """Test batch chunking for large token lists."""
        # Create 1000 tokens
        large_token_list = [f"token{i}_abc123def456" for i in range(1000)]
        
        # Mock FCM response
        mock_response = MagicMock()
        mock_response.success_count = 500
        mock_response.failure_count = 0
        mock_response.responses = [MagicMock(success=True) for _ in range(500)]
        mock_send.return_value = mock_response
        
        result = sender.send_notification(large_token_list, sample_payload)
        
        # Should be called twice (500 tokens per batch)
        assert mock_send.call_count == 2
        assert result.successCount == 1000
    
    def test_send_notification_empty_tokens(self, sender, sample_payload):
        """Test sending with empty token list."""
        result = sender.send_notification([], sample_payload)
        
        assert result.successCount == 0
        assert result.failureCount == 0
    
    @patch('app.notification_broadcaster.fcm_sender.messaging.send_multicast')
    def test_retry_failed_tokens(self, mock_send, sender, sample_payload, sample_tokens):
        """Test retrying failed tokens."""
        # First attempt: all fail
        mock_response1 = MagicMock()
        mock_response1.success_count = 0
        mock_response1.failure_count = 3
        mock_response1.responses = [
            MagicMock(success=False, exception=MagicMock(code="unavailable"))
            for _ in sample_tokens
        ]
        
        # Second attempt: all succeed
        mock_response2 = MagicMock()
        mock_response2.success_count = 3
        mock_response2.failure_count = 0
        mock_response2.responses = [
            MagicMock(success=True) for _ in sample_tokens
        ]
        
        mock_send.side_effect = [mock_response1, mock_response2]
        
        result = sender.retry_failed_tokens(sample_tokens, sample_payload, max_retries=2)
        
        assert result.successCount == 3
        assert mock_send.call_count == 2

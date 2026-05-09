"""Test notification broadcaster service."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.notification_broadcaster.schemas import (
    BatchSendResult,
    FCMToken,
    NotificationPayload,
)
from app.notification_broadcaster.service import NotificationBroadcasterService


@pytest.fixture
def service():
    """Create notification broadcaster service."""
    return NotificationBroadcasterService()


@pytest.fixture
def sample_payload():
    """Sample notification payload."""
    return NotificationPayload(
        title="Emergency Alert",
        body="Flooding in Ward-42",
        type="emergency",
        priority="high",
        targetRoles=["officer"],
        targetWards=["Ward-42"],
        data={"severity": "high"},
    )


@pytest.fixture
def sample_tokens():
    """Sample FCM tokens."""
    return [
        FCMToken(
            userId="user1",
            role="officer",
            ward="Ward-42",
            department="Roads",
            token="token1",
            active=True,
            lastSeen=datetime.utcnow(),
        ),
        FCMToken(
            userId="user2",
            role="officer",
            ward="Ward-42",
            department="Water",
            token="token2",
            active=True,
            lastSeen=datetime.utcnow(),
        ),
    ]


class TestNotificationBroadcasterService:
    """Test notification broadcaster service."""
    
    def test_broadcast_notification_success(self, service, sample_payload, sample_tokens):
        """Test successful notification broadcast."""
        with patch.object(service.token_repository, 'fetch_tokens_by_filter', return_value=sample_tokens), \
             patch.object(service.token_repository, 'deduplicate_tokens', return_value=["token1", "token2"]), \
             patch.object(service.batch_processor, 'process_batch', return_value=BatchSendResult(
                 successCount=2,
                 failureCount=0,
             )), \
             patch.object(service, '_log_notification'):
            
            result = service.broadcast_notification(sample_payload)
            
            assert result is not None
            assert result["successCount"] == 2
            assert result["failureCount"] == 0
            assert "notificationId" in result
    
    def test_broadcast_notification_with_invalid_tokens(self, service, sample_payload, sample_tokens):
        """Test broadcast with invalid tokens."""
        with patch.object(service.token_repository, 'fetch_tokens_by_filter', return_value=sample_tokens), \
             patch.object(service.token_repository, 'deduplicate_tokens', return_value=["token1", "token2"]), \
             patch.object(service.batch_processor, 'process_batch', return_value=BatchSendResult(
                 successCount=1,
                 failureCount=1,
                 invalidTokens=["token2"],
             )), \
             patch.object(service.cleanup_engine, 'cleanup_invalid_tokens', return_value=1), \
             patch.object(service, '_log_notification'):
            
            result = service.broadcast_notification(sample_payload)
            
            assert result is not None
            assert result["successCount"] == 1
            assert result["invalidTokensRemoved"] == 1
    
    def test_broadcast_notification_no_tokens(self, service, sample_payload):
        """Test broadcast with no matching tokens."""
        with patch.object(service.token_repository, 'fetch_tokens_by_filter', return_value=[]), \
             patch.object(service.token_repository, 'deduplicate_tokens', return_value=[]):
            
            result = service.broadcast_notification(sample_payload)
            
            assert result is not None
            assert result["successCount"] == 0
            assert "No matching tokens" in result["message"]
    
    def test_broadcast_to_role(self, service, sample_payload, sample_tokens):
        """Test broadcasting to specific role."""
        with patch.object(service, 'broadcast_notification', return_value={"successCount": 2}) as mock_broadcast:
            result = service.broadcast_to_role("officer", sample_payload)
            
            assert result is not None
            assert mock_broadcast.called
            assert sample_payload.targetRoles == ["officer"]
    
    def test_broadcast_to_ward(self, service, sample_payload, sample_tokens):
        """Test broadcasting to specific ward."""
        with patch.object(service, 'broadcast_notification', return_value={"successCount": 2}) as mock_broadcast:
            result = service.broadcast_to_ward("Ward-42", sample_payload)
            
            assert result is not None
            assert mock_broadcast.called
            assert sample_payload.targetWards == ["Ward-42"]
    
    def test_broadcast_to_department(self, service, sample_payload, sample_tokens):
        """Test broadcasting to specific department."""
        with patch.object(service, 'broadcast_notification', return_value={"successCount": 2}) as mock_broadcast:
            result = service.broadcast_to_department("Roads", sample_payload)
            
            assert result is not None
            assert mock_broadcast.called
            assert sample_payload.targetDepartments == ["Roads"]
    
    def test_broadcast_to_all(self, service, sample_payload):
        """Test broadcasting to all users."""
        with patch.object(service, 'broadcast_notification', return_value={"successCount": 100}) as mock_broadcast:
            result = service.broadcast_to_all(sample_payload)
            
            assert result is not None
            assert mock_broadcast.called
            assert sample_payload.targetRoles == []
            assert sample_payload.targetWards == []
            assert sample_payload.targetDepartments == []
    
    def test_generate_notification_id(self, service):
        """Test notification ID generation."""
        notification_id = service._generate_notification_id()
        
        assert notification_id.startswith("N")
        assert len(notification_id) > 10
    
    @patch('app.notification_broadcaster.service.get_firestore_client')
    def test_log_notification(self, mock_firestore, service, sample_payload):
        """Test notification logging."""
        mock_db = MagicMock()
        mock_firestore.return_value = mock_db
        
        service._log_notification(
            "N123456",
            sample_payload,
            success_count=10,
            failure_count=2,
            invalid_tokens_removed=1,
            errors=[],
        )
        
        mock_db.collection.assert_called_with("notification_logs")
    
    @patch('app.notification_broadcaster.service.get_firestore_client')
    def test_get_notification_log(self, mock_firestore, service):
        """Test getting notification log."""
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"notificationId": "N123456"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore.return_value = mock_db
        
        log = service.get_notification_log("N123456")
        
        assert log is not None
        assert log["notificationId"] == "N123456"

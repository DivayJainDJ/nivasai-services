"""Test complete notification broadcasting flow end-to-end."""

import pytest
from unittest.mock import MagicMock, patch


class TestNotificationFlow:
    """Test complete notification workflow."""
    
    def test_notification_broadcast_end_to_end(
        self,
        mock_firestore,
        mock_fcm,
        sample_notification_payload,
        sample_fcm_token,
    ):
        """Test notification broadcast from payload to delivery."""
        from app.notification_broadcaster.service import NotificationBroadcasterService
        from app.notification_broadcaster.schemas import NotificationPayload
        
        # Mock FCM tokens in Firestore
        mock_tokens = []
        for i in range(3):
            mock_doc = MagicMock()
            token = sample_fcm_token.copy()
            token["userId"] = f"user{i+1}"
            token["token"] = f"fcm_token_{i+1}"
            mock_doc.to_dict.return_value = token
            mock_tokens.append(mock_doc)
        
        mock_firestore.collection.return_value.where.return_value.stream.return_value = mock_tokens
        
        # Mock FCM send_multicast
        mock_response = MagicMock()
        mock_response.success_count = 3
        mock_response.failure_count = 0
        mock_response.responses = [MagicMock(success=True) for _ in range(3)]
        mock_fcm.return_value = mock_response
        
        # Broadcast notification
        service = NotificationBroadcasterService()
        payload = NotificationPayload(**sample_notification_payload)
        result = service.broadcast_notification(payload)
        
        assert result is not None
        assert result["successCount"] == 3
        assert result["failureCount"] == 0
        assert "notificationId" in result
    
    def test_role_based_targeting(
        self,
        mock_firestore,
        sample_fcm_token,
    ):
        """Test role-based notification targeting."""
        from app.notification_broadcaster.token_repository import TokenRepository
        
        repository = TokenRepository()
        
        # Mock tokens with different roles
        mock_tokens = []
        for role in ["officer", "officer", "supervisor"]:
            mock_doc = MagicMock()
            token = sample_fcm_token.copy()
            token["role"] = role
            mock_doc.to_dict.return_value = token
            mock_tokens.append(mock_doc)
        
        mock_firestore.collection.return_value.where.return_value.stream.return_value = mock_tokens
        
        # Fetch officer tokens
        tokens = repository.fetch_tokens_by_role("officer")
        
        assert len(tokens) == 2
        assert all(t.role == "officer" for t in tokens)
    
    def test_ward_based_targeting(
        self,
        mock_firestore,
        sample_fcm_token,
    ):
        """Test ward-based notification targeting."""
        from app.notification_broadcaster.token_repository import TokenRepository
        
        repository = TokenRepository()
        
        # Mock tokens with different wards
        mock_tokens = []
        for ward in ["Ward-42", "Ward-42", "Ward-23"]:
            mock_doc = MagicMock()
            token = sample_fcm_token.copy()
            token["ward"] = ward
            mock_doc.to_dict.return_value = token
            mock_tokens.append(mock_doc)
        
        mock_firestore.collection.return_value.where.return_value.stream.return_value = mock_tokens
        
        # Fetch Ward-42 tokens
        tokens = repository.fetch_tokens_by_ward("Ward-42")
        
        assert len(tokens) == 2
        assert all(t.ward == "Ward-42" for t in tokens)
    
    def test_invalid_token_cleanup(
        self,
        mock_firestore,
        mock_fcm,
    ):
        """Test invalid token cleanup after failed delivery."""
        from app.notification_broadcaster.cleanup_engine import CleanupEngine
        
        cleanup = CleanupEngine()
        
        # Mock Firestore token documents
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        # Cleanup invalid tokens
        invalid_tokens = ["fcm_token_invalid_1", "fcm_token_invalid_2"]
        removed = cleanup.cleanup_invalid_tokens(invalid_tokens)
        
        assert removed == 2
    
    def test_batch_processing(
        self,
        mock_fcm,
    ):
        """Test batch processing for large token lists."""
        from app.notification_broadcaster.batch_processor import BatchProcessor
        from app.notification_broadcaster.schemas import NotificationPayload
        
        processor = BatchProcessor()
        
        # Create large token list
        tokens = [f"fcm_token_{i}" for i in range(1000)]
        
        # Mock FCM response
        mock_response = MagicMock()
        mock_response.success_count = 500
        mock_response.failure_count = 0
        mock_response.responses = [MagicMock(success=True) for _ in range(500)]
        mock_fcm.return_value = mock_response
        
        payload = NotificationPayload(
            title="Test",
            body="Test notification",
            type="test",
            priority="normal",
        )
        
        result = processor.process_batch(tokens, payload)
        
        # Should process in 2 batches (500 each)
        assert result.successCount == 1000
        assert mock_fcm.call_count == 2
    
    def test_pubsub_integration(
        self,
        mock_pubsub,
        sample_notification_payload,
    ):
        """Test Pub/Sub integration for notification events."""
        from app.notification_broadcaster.pubsub_listener import PubSubListener
        from app.notification_broadcaster.schemas import NotificationPayload
        
        listener = PubSubListener()
        
        # Mock publisher
        mock_future = MagicMock()
        mock_future.result.return_value = "message_123"
        mock_pubsub["publisher"].return_value.publish.return_value = mock_future
        
        # Publish notification
        payload = NotificationPayload(**sample_notification_payload)
        success = listener.publish_notification(payload)
        
        assert success is True

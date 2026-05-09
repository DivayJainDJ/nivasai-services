"""Test token repository."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.notification_broadcaster.schemas import FCMToken, TokenFilter
from app.notification_broadcaster.token_repository import TokenRepository


@pytest.fixture
def repository():
    """Create token repository."""
    return TokenRepository()


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    with patch('app.notification_broadcaster.token_repository.get_firestore_client') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_tokens():
    """Sample FCM tokens."""
    return [
        FCMToken(
            userId="user1",
            role="officer",
            ward="Ward-42",
            department="Roads & Infrastructure",
            token="token1_abc123",
            active=True,
            lastSeen=datetime.utcnow(),
        ),
        FCMToken(
            userId="user2",
            role="officer",
            ward="Ward-42",
            department="Water Supply",
            token="token2_def456",
            active=True,
            lastSeen=datetime.utcnow(),
        ),
        FCMToken(
            userId="user3",
            role="supervisor",
            ward="Ward-23",
            department="Roads & Infrastructure",
            token="token3_ghi789",
            active=True,
            lastSeen=datetime.utcnow(),
        ),
    ]


class TestTokenRepository:
    """Test token repository."""
    
    def test_fetch_tokens_by_role(self, repository, mock_firestore, sample_tokens):
        """Test fetching tokens by role."""
        # Mock Firestore query
        mock_docs = [MagicMock() for _ in sample_tokens]
        for doc, token in zip(mock_docs, sample_tokens):
            doc.to_dict.return_value = token.model_dump(mode="json")
        
        mock_firestore.collection.return_value.where.return_value.stream.return_value = mock_docs
        
        tokens = repository.fetch_tokens_by_role("officer")
        
        assert len(tokens) == 2
        assert all(t.role == "officer" for t in tokens)
    
    def test_fetch_tokens_by_ward(self, repository, mock_firestore, sample_tokens):
        """Test fetching tokens by ward."""
        mock_docs = [MagicMock() for _ in sample_tokens]
        for doc, token in zip(mock_docs, sample_tokens):
            doc.to_dict.return_value = token.model_dump(mode="json")
        
        mock_firestore.collection.return_value.where.return_value.stream.return_value = mock_docs
        
        tokens = repository.fetch_tokens_by_ward("Ward-42")
        
        assert len(tokens) == 2
        assert all(t.ward == "Ward-42" for t in tokens)
    
    def test_fetch_tokens_by_department(self, repository, mock_firestore, sample_tokens):
        """Test fetching tokens by department."""
        mock_docs = [MagicMock() for _ in sample_tokens]
        for doc, token in zip(mock_docs, sample_tokens):
            doc.to_dict.return_value = token.model_dump(mode="json")
        
        mock_firestore.collection.return_value.where.return_value.stream.return_value = mock_docs
        
        tokens = repository.fetch_tokens_by_department("Roads & Infrastructure")
        
        assert len(tokens) == 2
        assert all(t.department == "Roads & Infrastructure" for t in tokens)
    
    def test_deduplicate_tokens(self, repository, sample_tokens):
        """Test token deduplication."""
        # Add duplicate
        duplicate_tokens = sample_tokens + [sample_tokens[0]]
        
        unique_tokens = repository.deduplicate_tokens(duplicate_tokens)
        
        assert len(unique_tokens) == 3
        assert len(set(unique_tokens)) == 3
    
    def test_deactivate_token(self, repository, mock_firestore):
        """Test deactivating token."""
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        result = repository.deactivate_token("token1_abc123")
        
        assert result is True
        mock_doc.reference.update.assert_called_once()
    
    def test_remove_token(self, repository, mock_firestore):
        """Test removing token."""
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        result = repository.remove_token("token1_abc123")
        
        assert result is True
        mock_doc.reference.delete.assert_called_once()
    
    def test_bulk_deactivate_tokens(self, repository, mock_firestore):
        """Test bulk token deactivation."""
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        tokens = ["token1", "token2", "token3"]
        count = repository.bulk_deactivate_tokens(tokens)
        
        assert count == 3
    
    def test_fetch_tokens_with_filter(self, repository, mock_firestore, sample_tokens):
        """Test fetching tokens with complex filter."""
        mock_docs = [MagicMock() for _ in sample_tokens]
        for doc, token in zip(mock_docs, sample_tokens):
            doc.to_dict.return_value = token.model_dump(mode="json")
        
        mock_firestore.collection.return_value.where.return_value.stream.return_value = mock_docs
        
        token_filter = TokenFilter(
            roles=["officer"],
            wards=["Ward-42"],
            activeOnly=True,
        )
        
        tokens = repository.fetch_tokens_by_filter(token_filter)
        
        assert len(tokens) == 2
        assert all(t.role == "officer" and t.ward == "Ward-42" for t in tokens)

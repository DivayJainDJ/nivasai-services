"""FCM token repository."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.notification_broadcaster.schemas import FCMToken, TokenFilter
from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class TokenRepository:
    """Repository for FCM token operations."""

    def __init__(self):
        """Initialize token repository."""
        self.collection_name = "fcm_tokens"

    def _get_firestore(self):
        """Get Firestore client."""
        return get_firestore_client()

    def fetch_tokens_by_filter(self, token_filter: TokenFilter) -> List[FCMToken]:
        """
        Fetch tokens matching filter criteria.
        
        Args:
            token_filter: Token filter criteria
        
        Returns:
            List of matching FCM tokens
        """
        try:
            db = self._get_firestore()
            query = db.collection(self.collection_name)
            
            # Filter by active status
            if token_filter.activeOnly:
                query = query.where("active", "==", True)
            
            # Fetch all documents
            docs = query.stream()
            
            tokens = []
            for doc in docs:
                try:
                    data = doc.to_dict()
                    token = FCMToken(**data)
                    
                    # Apply filters
                    if not self._matches_filter(token, token_filter):
                        continue
                    
                    tokens.append(token)
                
                except Exception as exc:
                    logger.error("token_parse_failed", doc_id=doc.id, error=str(exc))
                    continue
            
            logger.info(
                "tokens_fetched",
                count=len(tokens),
                roles=token_filter.roles,
                wards=token_filter.wards,
                departments=token_filter.departments,
            )
            
            return tokens
        
        except Exception as exc:
            logger.error("fetch_tokens_failed", error=str(exc))
            return []

    def _matches_filter(self, token: FCMToken, token_filter: TokenFilter) -> bool:
        """
        Check if token matches filter criteria.
        
        Args:
            token: FCM token
            token_filter: Filter criteria
        
        Returns:
            True if matches, False otherwise
        """
        # If no filters specified, match all
        if (
            not token_filter.roles and
            not token_filter.wards and
            not token_filter.departments
        ):
            return True
        
        # Check role filter
        if token_filter.roles and token.role not in token_filter.roles:
            return False
        
        # Check ward filter
        if token_filter.wards:
            if not token.ward or token.ward not in token_filter.wards:
                return False
        
        # Check department filter
        if token_filter.departments:
            if not token.department or token.department not in token_filter.departments:
                return False
        
        return True

    def fetch_all_active_tokens(self) -> List[FCMToken]:
        """
        Fetch all active tokens.
        
        Returns:
            List of all active FCM tokens
        """
        token_filter = TokenFilter(activeOnly=True)
        return self.fetch_tokens_by_filter(token_filter)

    def fetch_tokens_by_role(self, role: str) -> List[FCMToken]:
        """
        Fetch tokens by role.
        
        Args:
            role: User role
        
        Returns:
            List of matching tokens
        """
        token_filter = TokenFilter(roles=[role], activeOnly=True)
        return self.fetch_tokens_by_filter(token_filter)

    def fetch_tokens_by_ward(self, ward: str) -> List[FCMToken]:
        """
        Fetch tokens by ward.
        
        Args:
            ward: Ward identifier
        
        Returns:
            List of matching tokens
        """
        token_filter = TokenFilter(wards=[ward], activeOnly=True)
        return self.fetch_tokens_by_filter(token_filter)

    def fetch_tokens_by_department(self, department: str) -> List[FCMToken]:
        """
        Fetch tokens by department.
        
        Args:
            department: Department name
        
        Returns:
            List of matching tokens
        """
        token_filter = TokenFilter(departments=[department], activeOnly=True)
        return self.fetch_tokens_by_filter(token_filter)

    def deduplicate_tokens(self, tokens: List[FCMToken]) -> List[str]:
        """
        Deduplicate tokens and extract token strings.
        
        Args:
            tokens: List of FCM token objects
        
        Returns:
            List of unique token strings
        """
        seen = set()
        unique_tokens = []
        
        for token in tokens:
            if token.token not in seen:
                seen.add(token.token)
                unique_tokens.append(token.token)
        
        logger.info(
            "tokens_deduplicated",
            original_count=len(tokens),
            unique_count=len(unique_tokens),
        )
        
        return unique_tokens

    def deactivate_token(self, token: str) -> bool:
        """
        Deactivate an FCM token.
        
        Args:
            token: FCM token string
        
        Returns:
            True if successful, False otherwise
        """
        try:
            db = self._get_firestore()
            
            # Find token document
            query = db.collection(self.collection_name).where("token", "==", token).limit(1)
            docs = list(query.stream())
            
            if not docs:
                logger.warning("token_not_found_for_deactivation", token_prefix=token[:20])
                return False
            
            # Deactivate token
            doc = docs[0]
            doc.reference.update({
                "active": False,
                "deactivatedAt": datetime.utcnow(),
            })
            
            logger.info("token_deactivated", token_prefix=token[:20])
            return True
        
        except Exception as exc:
            logger.error("deactivate_token_failed", error=str(exc))
            return False

    def remove_token(self, token: str) -> bool:
        """
        Remove an FCM token from Firestore.
        
        Args:
            token: FCM token string
        
        Returns:
            True if successful, False otherwise
        """
        try:
            db = self._get_firestore()
            
            # Find token document
            query = db.collection(self.collection_name).where("token", "==", token).limit(1)
            docs = list(query.stream())
            
            if not docs:
                logger.warning("token_not_found_for_removal", token_prefix=token[:20])
                return False
            
            # Delete token
            doc = docs[0]
            doc.reference.delete()
            
            logger.info("token_removed", token_prefix=token[:20])
            return True
        
        except Exception as exc:
            logger.error("remove_token_failed", error=str(exc))
            return False

    def bulk_deactivate_tokens(self, tokens: List[str]) -> int:
        """
        Deactivate multiple tokens.
        
        Args:
            tokens: List of FCM token strings
        
        Returns:
            Number of tokens deactivated
        """
        count = 0
        for token in tokens:
            if self.deactivate_token(token):
                count += 1
        
        logger.info("bulk_deactivation_completed", count=count, total=len(tokens))
        return count

    def bulk_remove_tokens(self, tokens: List[str]) -> int:
        """
        Remove multiple tokens.
        
        Args:
            tokens: List of FCM token strings
        
        Returns:
            Number of tokens removed
        """
        count = 0
        for token in tokens:
            if self.remove_token(token):
                count += 1
        
        logger.info("bulk_removal_completed", count=count, total=len(tokens))
        return count

    def update_last_seen(self, token: str) -> bool:
        """
        Update last seen timestamp for token.
        
        Args:
            token: FCM token string
        
        Returns:
            True if successful, False otherwise
        """
        try:
            db = self._get_firestore()
            
            # Find token document
            query = db.collection(self.collection_name).where("token", "==", token).limit(1)
            docs = list(query.stream())
            
            if not docs:
                return False
            
            # Update last seen
            doc = docs[0]
            doc.reference.update({
                "lastSeen": datetime.utcnow(),
            })
            
            return True
        
        except Exception as exc:
            logger.error("update_last_seen_failed", error=str(exc))
            return False

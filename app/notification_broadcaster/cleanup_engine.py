"""Token cleanup engine."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from app.notification_broadcaster.token_repository import TokenRepository
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class CleanupEngine:
    """Engine for cleaning up invalid and expired tokens."""

    def __init__(self):
        """Initialize cleanup engine."""
        self.token_repository = TokenRepository()

    def cleanup_invalid_tokens(self, invalid_tokens: List[str]) -> int:
        """
        Clean up invalid tokens.
        
        Args:
            invalid_tokens: List of invalid FCM tokens
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            if not invalid_tokens:
                logger.info("no_invalid_tokens_to_cleanup")
                return 0
            
            logger.info("cleanup_started", token_count=len(invalid_tokens))
            
            # Remove invalid tokens
            removed_count = self.token_repository.bulk_remove_tokens(invalid_tokens)
            
            logger.info("cleanup_completed", removed=removed_count, total=len(invalid_tokens))
            
            return removed_count
        
        except Exception as exc:
            logger.error("cleanup_failed", error=str(exc))
            return 0

    def cleanup_expired_tokens(self, days_threshold: int = 90) -> int:
        """
        Clean up tokens not seen in specified days.
        
        Args:
            days_threshold: Number of days of inactivity before cleanup
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            logger.info("expired_cleanup_started", days_threshold=days_threshold)
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            
            # Fetch all tokens
            all_tokens = self.token_repository.fetch_all_active_tokens()
            
            # Find expired tokens
            expired_tokens = [
                token.token
                for token in all_tokens
                if token.lastSeen < cutoff_date
            ]
            
            if not expired_tokens:
                logger.info("no_expired_tokens_found")
                return 0
            
            logger.info("expired_tokens_found", count=len(expired_tokens))
            
            # Deactivate expired tokens
            deactivated_count = self.token_repository.bulk_deactivate_tokens(expired_tokens)
            
            logger.info("expired_cleanup_completed", deactivated=deactivated_count)
            
            return deactivated_count
        
        except Exception as exc:
            logger.error("expired_cleanup_failed", error=str(exc))
            return 0

    def cleanup_inactive_tokens(self, days_threshold: int = 30) -> int:
        """
        Deactivate tokens inactive for specified days.
        
        Args:
            days_threshold: Number of days of inactivity
        
        Returns:
            Number of tokens deactivated
        """
        try:
            logger.info("inactive_cleanup_started", days_threshold=days_threshold)
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            
            # Fetch all active tokens
            all_tokens = self.token_repository.fetch_all_active_tokens()
            
            # Find inactive tokens
            inactive_tokens = [
                token.token
                for token in all_tokens
                if token.lastSeen < cutoff_date
            ]
            
            if not inactive_tokens:
                logger.info("no_inactive_tokens_found")
                return 0
            
            logger.info("inactive_tokens_found", count=len(inactive_tokens))
            
            # Deactivate inactive tokens
            deactivated_count = self.token_repository.bulk_deactivate_tokens(inactive_tokens)
            
            logger.info("inactive_cleanup_completed", deactivated=deactivated_count)
            
            return deactivated_count
        
        except Exception as exc:
            logger.error("inactive_cleanup_failed", error=str(exc))
            return 0

    def cleanup_duplicate_tokens(self) -> int:
        """
        Clean up duplicate tokens for same user.
        
        Returns:
            Number of duplicates removed
        """
        try:
            logger.info("duplicate_cleanup_started")
            
            # Fetch all active tokens
            all_tokens = self.token_repository.fetch_all_active_tokens()
            
            # Group by userId
            user_tokens = {}
            for token in all_tokens:
                if token.userId not in user_tokens:
                    user_tokens[token.userId] = []
                user_tokens[token.userId].append(token)
            
            # Find duplicates
            duplicates_to_remove = []
            for user_id, tokens in user_tokens.items():
                if len(tokens) > 1:
                    # Keep most recent, remove others
                    sorted_tokens = sorted(tokens, key=lambda t: t.lastSeen, reverse=True)
                    duplicates = sorted_tokens[1:]  # Remove all except most recent
                    duplicates_to_remove.extend([t.token for t in duplicates])
            
            if not duplicates_to_remove:
                logger.info("no_duplicates_found")
                return 0
            
            logger.info("duplicates_found", count=len(duplicates_to_remove))
            
            # Remove duplicates
            removed_count = self.token_repository.bulk_remove_tokens(duplicates_to_remove)
            
            logger.info("duplicate_cleanup_completed", removed=removed_count)
            
            return removed_count
        
        except Exception as exc:
            logger.error("duplicate_cleanup_failed", error=str(exc))
            return 0

    def perform_full_cleanup(
        self,
        invalid_tokens: List[str] = None,
        inactive_days: int = 30,
        expired_days: int = 90,
        remove_duplicates: bool = True,
    ) -> dict:
        """
        Perform full cleanup operation.
        
        Args:
            invalid_tokens: List of invalid tokens to remove
            inactive_days: Days threshold for inactive tokens
            expired_days: Days threshold for expired tokens
            remove_duplicates: Whether to remove duplicate tokens
        
        Returns:
            Cleanup statistics
        """
        try:
            logger.info("full_cleanup_started")
            
            stats = {
                "invalid_removed": 0,
                "inactive_deactivated": 0,
                "expired_deactivated": 0,
                "duplicates_removed": 0,
            }
            
            # Clean up invalid tokens
            if invalid_tokens:
                stats["invalid_removed"] = self.cleanup_invalid_tokens(invalid_tokens)
            
            # Clean up inactive tokens
            stats["inactive_deactivated"] = self.cleanup_inactive_tokens(inactive_days)
            
            # Clean up expired tokens
            stats["expired_deactivated"] = self.cleanup_expired_tokens(expired_days)
            
            # Clean up duplicates
            if remove_duplicates:
                stats["duplicates_removed"] = self.cleanup_duplicate_tokens()
            
            logger.info("full_cleanup_completed", **stats)
            
            return stats
        
        except Exception as exc:
            logger.error("full_cleanup_failed", error=str(exc))
            return {
                "invalid_removed": 0,
                "inactive_deactivated": 0,
                "expired_deactivated": 0,
                "duplicates_removed": 0,
                "error": str(exc),
            }

    def get_cleanup_recommendations(self) -> dict:
        """
        Get cleanup recommendations based on current state.
        
        Returns:
            Recommendations dict
        """
        try:
            # Fetch all tokens
            all_tokens = self.token_repository.fetch_all_active_tokens()
            
            # Calculate statistics
            now = datetime.utcnow()
            inactive_30_days = sum(
                1 for t in all_tokens
                if (now - t.lastSeen).days > 30
            )
            inactive_90_days = sum(
                1 for t in all_tokens
                if (now - t.lastSeen).days > 90
            )
            
            # Check for duplicates
            user_ids = [t.userId for t in all_tokens]
            duplicate_count = len(user_ids) - len(set(user_ids))
            
            recommendations = {
                "total_active_tokens": len(all_tokens),
                "inactive_30_days": inactive_30_days,
                "inactive_90_days": inactive_90_days,
                "potential_duplicates": duplicate_count,
                "recommended_actions": [],
            }
            
            if inactive_30_days > 0:
                recommendations["recommended_actions"].append(
                    f"Deactivate {inactive_30_days} tokens inactive for 30+ days"
                )
            
            if inactive_90_days > 0:
                recommendations["recommended_actions"].append(
                    f"Remove {inactive_90_days} tokens inactive for 90+ days"
                )
            
            if duplicate_count > 0:
                recommendations["recommended_actions"].append(
                    f"Remove {duplicate_count} duplicate tokens"
                )
            
            logger.info("cleanup_recommendations_generated", **recommendations)
            
            return recommendations
        
        except Exception as exc:
            logger.error("recommendations_failed", error=str(exc))
            return {
                "error": str(exc),
            }

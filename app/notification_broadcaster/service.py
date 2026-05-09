"""Notification broadcaster service."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Optional

from app.notification_broadcaster.batch_processor import BatchProcessor
from app.notification_broadcaster.cleanup_engine import CleanupEngine
from app.notification_broadcaster.schemas import (
    NotificationLog,
    NotificationPayload,
    TokenFilter,
)
from app.notification_broadcaster.token_repository import TokenRepository
from app.notification_broadcaster.validator import validate_notification_payload
from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class NotificationBroadcasterService:
    """Main notification broadcaster service."""

    def __init__(self):
        """Initialize notification broadcaster service."""
        self.token_repository = TokenRepository()
        self.batch_processor = BatchProcessor()
        self.cleanup_engine = CleanupEngine()

    def broadcast_notification(self, payload: NotificationPayload) -> Optional[Dict]:
        """
        Broadcast notification to targeted users.
        
        Args:
            payload: Notification payload
        
        Returns:
            Broadcast result dict or None on failure
        """
        try:
            # Validate payload
            if not validate_notification_payload(payload):
                logger.error("invalid_notification_payload")
                return None
            
            logger.info(
                "broadcast_started",
                title=payload.title,
                type=payload.type,
                priority=payload.priority,
            )
            
            # Generate notification ID
            notification_id = self._generate_notification_id()
            
            # Fetch matching tokens
            tokens = self._fetch_target_tokens(payload)
            
            if not tokens:
                logger.warning("no_tokens_found_for_broadcast", title=payload.title)
                return {
                    "notificationId": notification_id,
                    "successCount": 0,
                    "failureCount": 0,
                    "invalidTokensRemoved": 0,
                    "message": "No matching tokens found",
                }
            
            logger.info("tokens_fetched_for_broadcast", count=len(tokens))
            
            # Send notifications in batches
            result = self.batch_processor.process_batch(tokens, payload)
            
            # Clean up invalid tokens
            invalid_count = 0
            if result.invalidTokens:
                invalid_count = self.cleanup_engine.cleanup_invalid_tokens(result.invalidTokens)
            
            # Log notification delivery
            self._log_notification(
                notification_id,
                payload,
                result.successCount,
                result.failureCount,
                invalid_count,
                result.errors,
            )
            
            logger.info(
                "broadcast_completed",
                notification_id=notification_id,
                success=result.successCount,
                failure=result.failureCount,
                invalid_removed=invalid_count,
            )
            
            return {
                "notificationId": notification_id,
                "successCount": result.successCount,
                "failureCount": result.failureCount,
                "invalidTokensRemoved": invalid_count,
                "totalTokens": len(tokens),
            }
        
        except Exception as exc:
            logger.error("broadcast_failed", error=str(exc))
            return None

    def _fetch_target_tokens(self, payload: NotificationPayload) -> list[str]:
        """
        Fetch tokens matching targeting criteria.
        
        Args:
            payload: Notification payload
        
        Returns:
            List of FCM token strings
        """
        try:
            # Build token filter
            token_filter = TokenFilter(
                roles=payload.targetRoles,
                wards=payload.targetWards,
                departments=payload.targetDepartments,
                activeOnly=True,
            )
            
            # Fetch matching tokens
            fcm_tokens = self.token_repository.fetch_tokens_by_filter(token_filter)
            
            # Deduplicate and extract token strings
            tokens = self.token_repository.deduplicate_tokens(fcm_tokens)
            
            logger.info(
                "target_tokens_fetched",
                count=len(tokens),
                roles=payload.targetRoles,
                wards=payload.targetWards,
                departments=payload.targetDepartments,
            )
            
            return tokens
        
        except Exception as exc:
            logger.error("fetch_target_tokens_failed", error=str(exc))
            return []

    def _generate_notification_id(self) -> str:
        """
        Generate unique notification ID.
        
        Returns:
            Notification ID
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"N{timestamp}{unique_id}"

    def _log_notification(
        self,
        notification_id: str,
        payload: NotificationPayload,
        success_count: int,
        failure_count: int,
        invalid_tokens_removed: int,
        errors: list[str],
    ) -> None:
        """
        Log notification delivery to Firestore.
        
        Args:
            notification_id: Notification ID
            payload: Notification payload
            success_count: Number of successful deliveries
            failure_count: Number of failed deliveries
            invalid_tokens_removed: Number of invalid tokens removed
            errors: List of error messages
        """
        try:
            db = get_firestore_client()
            
            log = NotificationLog(
                notificationId=notification_id,
                title=payload.title,
                body=payload.body,
                type=payload.type,
                priority=payload.priority,
                targetRoles=payload.targetRoles,
                targetWards=payload.targetWards,
                targetDepartments=payload.targetDepartments,
                successCount=success_count,
                failureCount=failure_count,
                invalidTokensRemoved=invalid_tokens_removed,
                sentAt=datetime.utcnow(),
                completedAt=datetime.utcnow(),
                errors=errors[:10],  # Limit to first 10 errors
            )
            
            db.collection("notification_logs").document(notification_id).set(
                log.model_dump(mode="json")
            )
            
            logger.info("notification_logged", notification_id=notification_id)
        
        except Exception as exc:
            logger.error("notification_logging_failed", error=str(exc))

    def broadcast_to_role(self, role: str, payload: NotificationPayload) -> Optional[Dict]:
        """
        Broadcast notification to specific role.
        
        Args:
            role: User role
            payload: Notification payload
        
        Returns:
            Broadcast result dict or None on failure
        """
        payload.targetRoles = [role]
        return self.broadcast_notification(payload)

    def broadcast_to_ward(self, ward: str, payload: NotificationPayload) -> Optional[Dict]:
        """
        Broadcast notification to specific ward.
        
        Args:
            ward: Ward identifier
            payload: Notification payload
        
        Returns:
            Broadcast result dict or None on failure
        """
        payload.targetWards = [ward]
        return self.broadcast_notification(payload)

    def broadcast_to_department(
        self,
        department: str,
        payload: NotificationPayload,
    ) -> Optional[Dict]:
        """
        Broadcast notification to specific department.
        
        Args:
            department: Department name
            payload: Notification payload
        
        Returns:
            Broadcast result dict or None on failure
        """
        payload.targetDepartments = [department]
        return self.broadcast_notification(payload)

    def broadcast_to_all(self, payload: NotificationPayload) -> Optional[Dict]:
        """
        Broadcast notification to all active users.
        
        Args:
            payload: Notification payload
        
        Returns:
            Broadcast result dict or None on failure
        """
        # Clear all targeting criteria to broadcast to all
        payload.targetRoles = []
        payload.targetWards = []
        payload.targetDepartments = []
        return self.broadcast_notification(payload)

    def get_notification_log(self, notification_id: str) -> Optional[Dict]:
        """
        Get notification log by ID.
        
        Args:
            notification_id: Notification ID
        
        Returns:
            Notification log dict or None if not found
        """
        try:
            db = get_firestore_client()
            doc = db.collection("notification_logs").document(notification_id).get()
            
            if not doc.exists:
                logger.warning("notification_log_not_found", notification_id=notification_id)
                return None
            
            return doc.to_dict()
        
        except Exception as exc:
            logger.error("get_notification_log_failed", error=str(exc))
            return None

    def get_notification_statistics(self, days: int = 7) -> Dict:
        """
        Get notification statistics for past days.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Statistics dict
        """
        try:
            db = get_firestore_client()
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Fetch recent logs
            logs = (
                db.collection("notification_logs")
                .where("sentAt", ">=", cutoff_date)
                .stream()
            )
            
            total_notifications = 0
            total_success = 0
            total_failure = 0
            total_invalid_removed = 0
            
            for log in logs:
                data = log.to_dict()
                total_notifications += 1
                total_success += data.get("successCount", 0)
                total_failure += data.get("failureCount", 0)
                total_invalid_removed += data.get("invalidTokensRemoved", 0)
            
            stats = {
                "days": days,
                "totalNotifications": total_notifications,
                "totalSuccess": total_success,
                "totalFailure": total_failure,
                "totalInvalidRemoved": total_invalid_removed,
                "successRate": (
                    round(total_success / (total_success + total_failure) * 100, 2)
                    if (total_success + total_failure) > 0
                    else 0
                ),
            }
            
            logger.info("notification_statistics_generated", **stats)
            
            return stats
        
        except Exception as exc:
            logger.error("get_statistics_failed", error=str(exc))
            return {}


from datetime import timedelta

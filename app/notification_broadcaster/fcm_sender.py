"""FCM notification sender."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from firebase_admin import messaging

from app.notification_broadcaster.schemas import BatchSendResult, NotificationPayload
from app.notification_broadcaster.validator import validate_fcm_token
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class FCMSender:
    """Firebase Cloud Messaging sender."""

    def __init__(self):
        """Initialize FCM sender."""
        self.max_batch_size = int(os.getenv("FCM_BATCH_SIZE", "500"))

    def send_notification(
        self,
        tokens: List[str],
        payload: NotificationPayload,
    ) -> BatchSendResult:
        """
        Send notification to multiple tokens.
        
        Args:
            tokens: List of FCM tokens
            payload: Notification payload
        
        Returns:
            BatchSendResult with delivery statistics
        """
        try:
            if not tokens:
                logger.warning("no_tokens_to_send")
                return BatchSendResult()
            
            logger.info(
                "fcm_send_started",
                token_count=len(tokens),
                title=payload.title,
                priority=payload.priority,
            )
            
            # Build FCM message
            message = self._build_fcm_message(payload)
            
            # Send in batches
            result = self._send_multicast(tokens, message, payload)
            
            logger.info(
                "fcm_send_completed",
                success=result.successCount,
                failure=result.failureCount,
                invalid=len(result.invalidTokens),
            )
            
            return result
        
        except Exception as exc:
            logger.error("fcm_send_failed", error=str(exc))
            return BatchSendResult(
                failureCount=len(tokens),
                errors=[str(exc)],
            )

    def _build_fcm_message(self, payload: NotificationPayload) -> Dict[str, Any]:
        """
        Build FCM message from payload.
        
        Args:
            payload: Notification payload
        
        Returns:
            FCM message dict
        """
        # Convert data dict to string values (FCM requirement)
        data = {}
        for key, value in payload.data.items():
            data[key] = str(value)
        
        # Add metadata
        data["type"] = payload.type
        data["priority"] = payload.priority
        
        message = {
            "notification": {
                "title": payload.title,
                "body": payload.body,
            },
            "data": data,
        }
        
        # Add Android-specific config
        if payload.priority == "high":
            message["android"] = {
                "priority": "high",
                "notification": {
                    "sound": "default",
                    "channel_id": "high_priority",
                },
            }
        else:
            message["android"] = {
                "priority": "normal",
                "notification": {
                    "sound": "default",
                },
            }
        
        # Add iOS-specific config
        if payload.priority == "high":
            message["apns"] = {
                "headers": {
                    "apns-priority": "10",
                },
                "payload": {
                    "aps": {
                        "sound": "default",
                        "badge": 1,
                    },
                },
            }
        else:
            message["apns"] = {
                "headers": {
                    "apns-priority": "5",
                },
                "payload": {
                    "aps": {
                        "sound": "default",
                    },
                },
            }
        
        return message

    def _send_multicast(
        self,
        tokens: List[str],
        message: Dict[str, Any],
        payload: NotificationPayload,
    ) -> BatchSendResult:
        """
        Send multicast message to tokens.
        
        Args:
            tokens: List of FCM tokens
            message: FCM message dict
            payload: Original notification payload
        
        Returns:
            BatchSendResult
        """
        result = BatchSendResult()
        
        # Validate tokens
        valid_tokens = [t for t in tokens if validate_fcm_token(t)]
        invalid_count = len(tokens) - len(valid_tokens)
        
        if invalid_count > 0:
            logger.warning("invalid_tokens_filtered", count=invalid_count)
            result.failureCount += invalid_count
        
        if not valid_tokens:
            logger.warning("no_valid_tokens_to_send")
            return result
        
        # Send in chunks
        chunk_size = min(self.max_batch_size, 500)  # FCM limit is 500
        
        for i in range(0, len(valid_tokens), chunk_size):
            chunk = valid_tokens[i:i + chunk_size]
            chunk_result = self._send_chunk(chunk, message, payload)
            
            # Aggregate results
            result.successCount += chunk_result.successCount
            result.failureCount += chunk_result.failureCount
            result.invalidTokens.extend(chunk_result.invalidTokens)
            result.errors.extend(chunk_result.errors)
        
        return result

    def _send_chunk(
        self,
        tokens: List[str],
        message: Dict[str, Any],
        payload: NotificationPayload,
    ) -> BatchSendResult:
        """
        Send notification to a chunk of tokens.
        
        Args:
            tokens: List of FCM tokens (max 500)
            message: FCM message dict
            payload: Original notification payload
        
        Returns:
            BatchSendResult for this chunk
        """
        result = BatchSendResult()
        
        try:
            # Build multicast message
            multicast_message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=message["notification"]["title"],
                    body=message["notification"]["body"],
                ),
                data=message["data"],
                android=messaging.AndroidConfig(
                    priority=message["android"]["priority"],
                    notification=messaging.AndroidNotification(
                        sound=message["android"]["notification"]["sound"],
                        channel_id=message["android"]["notification"].get("channel_id"),
                    ),
                ),
                apns=messaging.APNSConfig(
                    headers=message["apns"]["headers"],
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=message["apns"]["payload"]["aps"]["sound"],
                            badge=message["apns"]["payload"]["aps"].get("badge"),
                        ),
                    ),
                ),
                tokens=tokens,
            )
            
            # Send multicast
            response = messaging.send_multicast(multicast_message)
            
            logger.info(
                "chunk_sent",
                success=response.success_count,
                failure=response.failure_count,
                total=len(tokens),
            )
            
            # Process responses
            result.successCount = response.success_count
            result.failureCount = response.failure_count
            
            # Identify invalid tokens
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    error = resp.exception
                    if error:
                        error_code = getattr(error, "code", None)
                        
                        # Check for invalid token errors
                        if error_code in [
                            "invalid-registration-token",
                            "registration-token-not-registered",
                            "invalid-argument",
                        ]:
                            result.invalidTokens.append(tokens[idx])
                            logger.warning(
                                "invalid_token_detected",
                                token_prefix=tokens[idx][:20],
                                error_code=error_code,
                            )
                        else:
                            result.errors.append(f"{error_code}: {str(error)}")
            
            return result
        
        except Exception as exc:
            logger.error("chunk_send_failed", error=str(exc), token_count=len(tokens))
            result.failureCount = len(tokens)
            result.errors.append(str(exc))
            return result

    def send_to_topic(self, topic: str, payload: NotificationPayload) -> bool:
        """
        Send notification to a topic.
        
        Args:
            topic: FCM topic name
            payload: Notification payload
        
        Returns:
            True if successful, False otherwise
        """
        try:
            message = self._build_fcm_message(payload)
            
            topic_message = messaging.Message(
                notification=messaging.Notification(
                    title=message["notification"]["title"],
                    body=message["notification"]["body"],
                ),
                data=message["data"],
                android=messaging.AndroidConfig(
                    priority=message["android"]["priority"],
                    notification=messaging.AndroidNotification(
                        sound=message["android"]["notification"]["sound"],
                    ),
                ),
                topic=topic,
            )
            
            response = messaging.send(topic_message)
            
            logger.info("topic_notification_sent", topic=topic, message_id=response)
            return True
        
        except Exception as exc:
            logger.error("topic_send_failed", topic=topic, error=str(exc))
            return False

    def retry_failed_tokens(
        self,
        tokens: List[str],
        payload: NotificationPayload,
        max_retries: int = 2,
    ) -> BatchSendResult:
        """
        Retry sending to failed tokens.
        
        Args:
            tokens: List of tokens that failed
            payload: Notification payload
            max_retries: Maximum retry attempts
        
        Returns:
            BatchSendResult
        """
        result = BatchSendResult()
        remaining_tokens = tokens.copy()
        
        for attempt in range(max_retries):
            if not remaining_tokens:
                break
            
            logger.info("retry_attempt", attempt=attempt + 1, token_count=len(remaining_tokens))
            
            retry_result = self.send_notification(remaining_tokens, payload)
            
            result.successCount += retry_result.successCount
            result.failureCount += retry_result.failureCount
            result.invalidTokens.extend(retry_result.invalidTokens)
            
            # Remove successful and invalid tokens from retry list
            remaining_tokens = [
                t for t in remaining_tokens
                if t not in retry_result.invalidTokens
            ]
            
            # If all succeeded, break
            if retry_result.failureCount == 0:
                break
        
        logger.info(
            "retry_completed",
            final_success=result.successCount,
            final_failure=result.failureCount,
        )
        
        return result

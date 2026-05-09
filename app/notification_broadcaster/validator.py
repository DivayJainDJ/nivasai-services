"""Notification payload validator."""

from __future__ import annotations

from typing import Any, Dict, List

from app.notification_broadcaster.schemas import NotificationPayload
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


def validate_pubsub_payload(payload: Dict[str, Any]) -> bool:
    """
    Validate Pub/Sub payload.
    
    Args:
        payload: Raw Pub/Sub payload
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required fields
        required_fields = ["title", "body", "type"]
        for field in required_fields:
            if field not in payload:
                logger.error("validation_failed", reason=f"missing_field_{field}")
                return False
            if not payload[field]:
                logger.error("validation_failed", reason=f"empty_field_{field}")
                return False
        
        # Validate title length
        if len(payload["title"]) > 100:
            logger.error("validation_failed", reason="title_too_long", length=len(payload["title"]))
            return False
        
        # Validate body length
        if len(payload["body"]) > 500:
            logger.error("validation_failed", reason="body_too_long", length=len(payload["body"]))
            return False
        
        # Validate priority if present
        if "priority" in payload:
            if payload["priority"] not in ["normal", "high"]:
                logger.error("validation_failed", reason="invalid_priority", priority=payload["priority"])
                return False
        
        # Validate target lists are lists
        list_fields = ["targetRoles", "targetWards", "targetDepartments"]
        for field in list_fields:
            if field in payload and not isinstance(payload[field], list):
                logger.error("validation_failed", reason=f"invalid_type_{field}")
                return False
        
        # Validate data is dict
        if "data" in payload and not isinstance(payload["data"], dict):
            logger.error("validation_failed", reason="invalid_data_type")
            return False
        
        logger.info("payload_validated", title=payload["title"])
        return True
    
    except Exception as exc:
        logger.error("validation_exception", error=str(exc))
        return False


def validate_notification_payload(payload: NotificationPayload) -> bool:
    """
    Validate notification payload object.
    
    Args:
        payload: NotificationPayload object
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check at least one targeting criteria
        has_targeting = (
            len(payload.targetRoles) > 0 or
            len(payload.targetWards) > 0 or
            len(payload.targetDepartments) > 0
        )
        
        if not has_targeting:
            logger.warning("no_targeting_criteria", title=payload.title)
            # Allow broadcast to all if no targeting specified
        
        # Validate priority
        if payload.priority not in ["normal", "high"]:
            logger.error("invalid_priority", priority=payload.priority)
            return False
        
        # Validate title and body
        if not payload.title or not payload.body:
            logger.error("empty_title_or_body")
            return False
        
        logger.info("notification_payload_validated", title=payload.title, type=payload.type)
        return True
    
    except Exception as exc:
        logger.error("notification_validation_exception", error=str(exc))
        return False


def validate_fcm_token(token: str) -> bool:
    """
    Validate FCM token format.
    
    Args:
        token: FCM token string
    
    Returns:
        True if valid format, False otherwise
    """
    try:
        # Basic validation
        if not token:
            return False
        
        # FCM tokens are typically 152+ characters
        if len(token) < 50:
            logger.warning("token_too_short", length=len(token))
            return False
        
        # Check for valid characters (alphanumeric, hyphens, underscores, colons)
        if not all(c.isalnum() or c in ["-", "_", ":"] for c in token):
            logger.warning("token_invalid_characters")
            return False
        
        return True
    
    except Exception as exc:
        logger.error("token_validation_exception", error=str(exc))
        return False


def validate_token_list(tokens: List[str]) -> List[str]:
    """
    Validate and filter token list.
    
    Args:
        tokens: List of FCM tokens
    
    Returns:
        List of valid tokens
    """
    valid_tokens = []
    
    for token in tokens:
        if validate_fcm_token(token):
            valid_tokens.append(token)
        else:
            logger.warning("invalid_token_filtered", token_prefix=token[:20] if token else "")
    
    logger.info("tokens_validated", total=len(tokens), valid=len(valid_tokens))
    return valid_tokens


def validate_batch_size(batch_size: int, max_size: int = 500) -> bool:
    """
    Validate batch size.
    
    Args:
        batch_size: Requested batch size
        max_size: Maximum allowed batch size
    
    Returns:
        True if valid, False otherwise
    """
    if batch_size <= 0:
        logger.error("invalid_batch_size", size=batch_size, reason="non_positive")
        return False
    
    if batch_size > max_size:
        logger.error("invalid_batch_size", size=batch_size, max=max_size, reason="too_large")
        return False
    
    return True

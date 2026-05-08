"""
Audit logging for compliance and security.
"""

from app.shared.logging.logger import get_logger


class AuditLogger:
    """Logger for audit trails and security events."""

    def __init__(self):
        """Initialize audit logger."""
        self.logger = get_logger("audit")

    def log_access(self, user_id: str, action: str, resource: str):
        """Log resource access."""
        self.logger.info(
            "Access logged",
            user_id=user_id,
            action=action,
            resource=resource,
        )

    def log_data_modification(self, user_id: str, entity_type: str, entity_id: str):
        """Log data modifications."""
        self.logger.info(
            "Data modified",
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    def log_escalation(self, complaint_id: str, reason: str):
        """Log escalation events."""
        self.logger.info(
            "Escalation triggered",
            complaint_id=complaint_id,
            reason=reason,
        )

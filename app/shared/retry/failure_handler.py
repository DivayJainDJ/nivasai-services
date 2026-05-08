"""
Failure handling and recovery strategies.
"""

from app.shared.logging.error_logger import ErrorLogger


class FailureHandler:
    """Handles failures and recovery logic."""

    def __init__(self, service_name: str):
        """Initialize failure handler."""
        self.error_logger = ErrorLogger(service_name)
        self.service_name = service_name

    def handle_parsing_failure(self, error: str, context: dict):
        """Handle parsing failures."""
        self.error_logger.log_parsing_error(error, context)
        raise ValueError(f"Parsing failed: {error}")

    def handle_validation_failure(self, field: str, value: str, reason: str):
        """Handle validation failures."""
        self.error_logger.log_validation_error(field, value, reason)
        raise ValueError(f"Validation failed for {field}: {reason}")

    def handle_api_failure(self, status_code: int, error: str, endpoint: str):
        """Handle API failures."""
        self.error_logger.log_api_error(status_code, error, endpoint)
        raise RuntimeError(f"API error from {endpoint}: {error}")

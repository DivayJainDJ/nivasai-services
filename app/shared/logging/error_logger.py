"""
Error-specific logging utilities.
"""

from app.shared.logging.logger import get_logger


class ErrorLogger:
    """Specialized logger for error tracking and reporting."""

    def __init__(self, service_name: str):
        """Initialize error logger."""
        self.logger = get_logger(f"{service_name}.errors")

    def log_parsing_error(self, error: str, context: dict):
        """Log parsing errors."""
        self.logger.error(
            "Parsing error",
            error=error,
            service=context.get("service"),
            input_sample=str(context.get("input", ""))[:100],
        )

    def log_api_error(self, status_code: int, error: str, endpoint: str):
        """Log API errors."""
        self.logger.error(
            "API error",
            status_code=status_code,
            error=error,
            endpoint=endpoint,
        )

    def log_validation_error(self, field: str, value: str, reason: str):
        """Log validation errors."""
        self.logger.error(
            "Validation error",
            field=field,
            value=str(value)[:50],
            reason=reason,
        )

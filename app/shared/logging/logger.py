"""
Structured logging for NivasAI services.

Provides cloud-compatible logging with structured output.
"""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime


class StructuredLogger:
    """Structured logger with JSON formatting."""

    def __init__(self, name: str):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

    def _format_log(
        self, level: str, message: str, **kwargs
    ) -> Dict[str, Any]:
        """Format log entry as structured JSON."""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            "logger": self.logger.name,
            **kwargs,
        }

    def info(self, message: str, **kwargs):
        """Log info level message."""
        log_entry = self._format_log("INFO", message, **kwargs)
        self.logger.info(json.dumps(log_entry))

    def error(self, message: str, **kwargs):
        """Log error level message."""
        log_entry = self._format_log("ERROR", message, **kwargs)
        self.logger.error(json.dumps(log_entry))

    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        log_entry = self._format_log("WARNING", message, **kwargs)
        self.logger.warning(json.dumps(log_entry))

    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        log_entry = self._format_log("DEBUG", message, **kwargs)
        self.logger.debug(json.dumps(log_entry))


def get_logger(name: str) -> StructuredLogger:
    """Get or create logger instance."""
    return StructuredLogger(name)

"""
Application dependencies and initialization.

Manages singleton instances of clients and services.
"""

from functools import lru_cache

from app.config import settings
from app.shared.gemini.client import model as gemini_model
from app.shared.logging.logger import get_logger


logger = get_logger(__name__)


@lru_cache()
def get_settings():
    """Get application settings."""
    return settings


@lru_cache()
def get_gemini_model():
    """Get Gemini AI model instance."""
    return gemini_model


@lru_cache()
def get_logger_instance(name: str):
    """Get logger instance."""
    return get_logger(name)

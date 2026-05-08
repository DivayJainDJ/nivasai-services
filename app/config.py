"""
Application configuration for NivasAI.

Centralized settings management using environment variables.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment variables."""

    # Gemini AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "nivasai-dev")
    FIRESTORE_COLLECTION_PREFIX: str = "nivasai"

    # Maps Configuration
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY")

    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER")

    # Document AI Configuration
    DOCUMENT_AI_PROJECT_ID: str = os.getenv("DOCUMENT_AI_PROJECT_ID")
    DOCUMENT_AI_LOCATION: str = os.getenv("DOCUMENT_AI_LOCATION", "us")
    DOCUMENT_AI_PROCESSOR_ID: str = os.getenv("DOCUMENT_AI_PROCESSOR_ID")

    # BigQuery Configuration
    BIGQUERY_PROJECT_ID: str = os.getenv("BIGQUERY_PROJECT_ID")
    BIGQUERY_DATASET: str = os.getenv("BIGQUERY_DATASET", "nivasai_analytics")

    # Cloud Storage Configuration
    CLOUD_STORAGE_BUCKET: str = os.getenv("CLOUD_STORAGE_BUCKET")

    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        """Initialize settings and validate required configuration."""
        required_keys = ["GEMINI_API_KEY"]
        missing_keys = [key for key in required_keys if not getattr(self, key, None)]
        
        if missing_keys:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_keys)}"
            )

    def __repr__(self):
        """Safe representation of settings without exposing secrets."""
        return (
            f"Settings(DEBUG={self.DEBUG}, LOG_LEVEL={self.LOG_LEVEL}, "
            f"GEMINI_MODEL={self.GEMINI_MODEL}, FIREBASE_PROJECT={self.FIREBASE_PROJECT_ID})"
        )


# Global settings instance
settings = Settings()

"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "NivasAI Backend"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://nivasai-app.web.app",
        "https://nivasai-app.firebaseapp.com"
    ]
    
    # Firebase
    FIREBASE_PROJECT_ID: str
    FIREBASE_API_KEY: str
    FIREBASE_AUTH_DOMAIN: str
    FIREBASE_STORAGE_BUCKET: str
    FIREBASE_MESSAGING_SENDER_ID: str
    FIREBASE_APP_ID: str
    
    # Google AI
    GEMINI_API_KEY: str
    GOOGLE_MAPS_API_KEY: str
    
    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # Document AI
    DOCUMENT_AI_PROJECT_ID: Optional[str] = None
    DOCUMENT_AI_LOCATION: str = "us"
    DOCUMENT_AI_PROCESSOR_ID: Optional[str] = None
    
    # BigQuery
    BIGQUERY_DATASET: str = "nivasai_analytics"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY_MS: int = 1000
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Validate required settings
def validate_settings():
    """Validate required configuration"""
    required_settings = [
        "FIREBASE_PROJECT_ID",
        "FIREBASE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_MAPS_API_KEY"
    ]
    
    missing_settings = []
    for setting in required_settings:
        if not getattr(settings, setting):
            missing_settings.append(setting)
    
    if missing_settings:
        raise ValueError(f"Missing required settings: {missing_settings}")


# Validate on import
validate_settings()

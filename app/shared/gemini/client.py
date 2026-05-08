"""
Gemini API client initialization and configuration.

Provides centralized, reusable model instance for all AI services.
"""

import google.generativeai as genai

from app.config import settings


def initialize_gemini_client() -> genai.GenerativeModel:
    """
    Initialize and configure Gemini client.

    Returns:
        Configured GenerativeModel instance
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        generation_config={
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        },
    )


# Global model instance - reusable across all services
model = initialize_gemini_client()

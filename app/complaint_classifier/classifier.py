"""Gemini vision classifier implementation."""

from __future__ import annotations

import time

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.complaint_classifier.prompt_builder import build_classification_prompt
from app.complaint_classifier.schemas import ClassificationResult
from app.complaint_classifier.validator import parse_model_json, validate_classification_payload
from app.config import settings
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

MODEL_NAME = "gemini-2.5-flash"
_gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)


class GeminiClassificationError(Exception):
    """Raised when Gemini classification fails."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((TimeoutError, ConnectionError, GeminiClassificationError)),
    reraise=True,
)
def classify_from_image_and_text(
    *,
    image_bytes: bytes,
    mime_type: str,
    description: str,
) -> ClassificationResult:
    """Classify complaint from image+text using Gemini."""
    prompt = build_classification_prompt(description)
    start = time.perf_counter()
    try:
        response = _gemini_client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        raise GeminiClassificationError(f"Gemini request failed: {exc}") from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info("gemini_latency", latency_ms=latency_ms)

    response_text = getattr(response, "text", "")
    if not response_text:
        raise GeminiClassificationError("Empty Gemini response")

    try:
        parsed = parse_model_json(response_text)
    except Exception as exc:
        raise GeminiClassificationError(f"Malformed Gemini JSON: {exc}") from exc

    return validate_classification_payload(parsed)

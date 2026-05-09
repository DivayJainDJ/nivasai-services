"""Gemini Vision infrastructure scorer."""

from __future__ import annotations

import time
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.shared.logging.logger import get_logger
from app.ward_analyzer.validator import parse_json_object, validate_vision_payload

logger = get_logger(__name__)
_MODEL = "gemini-2.5-flash"
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy initialization of Gemini client to avoid startup crashes."""
    global _client
    if _client is None:
        try:
            _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as exc:
            logger.error("gemini_client_init_failed", error=str(exc))
            raise VisionScoringError(f"Failed to initialize Gemini client: {exc}") from exc
    return _client


class VisionScoringError(Exception):
    """Raised when Gemini vision scoring fails."""


_VISION_PROMPT = """
You are a municipal infrastructure vision analyst.
Analyze the satellite image and return only JSON:
{
  "roadQuality": 0-100,
  "drainageQuality": 0-100,
  "sanitationQuality": 0-100,
  "greenCoverage": 0-100,
  "housingDensity": 0-100,
  "floodRisk": 0-100,
  "summary": "short factual summary",
  "confidence": 0.0-1.0
}
Score by visible patterns only. No markdown. No extra keys.
""".strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
def score_infrastructure_from_satellite(image_bytes: bytes, mime_type: str):
    """Run Gemini vision scoring for municipal infrastructure metrics."""
    client = _get_client()
    started = time.perf_counter()
    
    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), _VISION_PROMPT],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        logger.error("gemini_vision_request_failed", error=str(exc))
        raise VisionScoringError(f"Vision request failed: {exc}") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info("gemini_latency", stage="vision", latency_ms=latency_ms)

    raw = getattr(response, "text", "")
    if not raw:
        raise VisionScoringError("Empty Gemini vision response")

    try:
        parsed = parse_json_object(raw)
        payload = validate_vision_payload(parsed)
        return payload
    except Exception as exc:
        logger.error("gemini_vision_parse_failed", error=str(exc))
        raise VisionScoringError(f"Malformed vision payload: {exc}") from exc

"""Gemini text remediation planner using infrastructure scores."""

from __future__ import annotations

import time
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.shared.logging.logger import get_logger
from app.ward_analyzer.validator import RemediationPayload, parse_json_object, validate_remediation_payload

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
            raise RemediationGenerationError(f"Failed to initialize Gemini client: {exc}") from exc
    return _client


class RemediationGenerationError(Exception):
    """Raised when remediation generation fails."""


def _build_remediation_prompt(
    *,
    ward_name: str,
    city: str,
    state: str,
    population: int,
    scores: dict,
) -> str:
    return f"""
You are a municipal planning AI.
Use the ward context and infrastructure scores to generate a practical remediation strategy.
Budget must be realistic INR with local fixes in lakhs and ward upgrades in crores where needed.
Return only JSON with keys:
{{
  "priorityLevel": "",
  "keyProblems": [],
  "recommendedProjects": [],
  "estimatedBudgetINR": 0,
  "executionTimeline": "",
  "riskAssessment": "",
  "phasedPlan": [],
  "summary": ""
}}

Ward: {ward_name}, City: {city}, State: {state}, Population: {population}
Scores: {scores}
""".strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
def generate_remediation_plan(
    *,
    ward_name: str,
    city: str,
    state: str,
    population: int,
    scores_payload,
) -> RemediationPayload:
    """Generate remediation strategy from validated score payload."""
    client = _get_client()
    
    prompt = _build_remediation_prompt(
        ward_name=ward_name,
        city=city,
        state=state,
        population=population,
        scores=scores_payload.model_dump(),
    )
    started = time.perf_counter()
    
    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        logger.error("gemini_remediation_request_failed", error=str(exc))
        raise RemediationGenerationError(f"Remediation request failed: {exc}") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info("gemini_latency", stage="remediation", latency_ms=latency_ms)

    raw = getattr(response, "text", "")
    if not raw:
        raise RemediationGenerationError("Empty Gemini remediation response")

    try:
        parsed = parse_json_object(raw)
        return validate_remediation_payload(parsed)
    except Exception as exc:
        logger.error("gemini_remediation_parse_failed", error=str(exc))
        raise RemediationGenerationError(f"Malformed remediation payload: {exc}") from exc

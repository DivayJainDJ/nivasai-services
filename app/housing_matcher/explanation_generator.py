"""Gemini-powered explanation generator for housing matches."""

from __future__ import annotations

import os
import time
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.housing_matcher.schemas import CitizenInput, GeminiExplanation, HousingUnit, RankingScore
from app.housing_matcher.validator import parse_json_response, validate_gemini_explanation
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

_MODEL = "gemini-2.5-flash"
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy initialization of Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ExplanationGenerationError("GEMINI_API_KEY not configured")
        
        try:
            _client = genai.Client(api_key=api_key)
        except Exception as exc:
            logger.error("gemini_client_init_failed", error=str(exc))
            raise ExplanationGenerationError(f"Failed to initialize Gemini client: {exc}") from exc
    
    return _client


class ExplanationGenerationError(Exception):
    """Raised when explanation generation fails."""


class ExplanationGenerator:
    """Generate bilingual explanations for housing matches using Gemini."""

    def __init__(self, citizen: CitizenInput):
        """Initialize explanation generator with citizen data."""
        self.citizen = citizen

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        reraise=True,
    )
    def generate_explanation(
        self,
        unit: HousingUnit,
        score: RankingScore,
        distance_km: float,
        eligibility_reason: str,
    ) -> GeminiExplanation:
        """Generate bilingual explanation for a housing match."""
        client = _get_client()
        
        prompt = self._build_prompt(unit, score, distance_km, eligibility_reason)
        
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
            logger.error("gemini_explanation_request_failed", error=str(exc), unit_id=unit.unitId)
            raise ExplanationGenerationError(f"Explanation request failed: {exc}") from exc
        
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info("gemini_latency", stage="explanation", latency_ms=latency_ms, unit_id=unit.unitId)
        
        raw = getattr(response, "text", "")
        if not raw:
            raise ExplanationGenerationError("Empty Gemini response")
        
        try:
            parsed = parse_json_response(raw)
            explanation = validate_gemini_explanation(parsed)
            return explanation
        except Exception as exc:
            logger.error("gemini_explanation_parse_failed", error=str(exc), unit_id=unit.unitId)
            raise ExplanationGenerationError(f"Malformed explanation: {exc}") from exc

    def _build_prompt(
        self,
        unit: HousingUnit,
        score: RankingScore,
        distance_km: float,
        eligibility_reason: str,
    ) -> str:
        """Build prompt for Gemini explanation generation."""
        return f"""You are a housing assistance AI helping citizens find affordable housing.

Generate a bilingual explanation for this housing match.

CITIZEN DETAILS:
- Name: {self.citizen.citizenName}
- Monthly Income: ₹{self.citizen.monthlyIncome:,}
- Family Size: {self.citizen.familySize}
- City: {self.citizen.city}
- Category: {self.citizen.category}
- Urgency: {self.citizen.urgencyLevel}

HOUSING UNIT:
- Unit ID: {unit.unitId}
- Scheme: {unit.scheme}
- Price: ₹{unit.priceINR:,}
- Capacity: {unit.capacity} people
- Max Income: ₹{unit.maxIncome:,}
- Distance: {distance_km} km
- Address: {unit.address or "Not specified"}

MATCH SCORES:
- Overall Score: {score.totalScore}/100
- Affordability: {score.affordabilityScore}/100
- Distance: {score.distanceScore}/100
- Occupancy Fit: {score.occupancyScore}/100

ELIGIBILITY:
{eligibility_reason}

Generate a JSON response with these exact keys:
{{
  "englishExplanation": "A warm, helpful explanation in English (100-200 words) explaining why this unit is a good match, highlighting affordability, location, and suitability for the family.",
  "hindiExplanation": "Same explanation in Hindi (हिंदी में समझाएं) - natural, conversational Hindi explaining the match benefits.",
  "eligibilityReason": "Clear explanation of why the citizen qualifies for this unit (50-100 words).",
  "documentChecklist": [
    "List of 5-8 required documents for application",
    "Include: Aadhaar card, income certificate, etc.",
    "Be specific to the scheme and category"
  ],
  "nextSteps": [
    "List of 3-5 clear action steps",
    "Start with 'Visit the housing office...'",
    "Include application submission steps"
  ]
}}

IMPORTANT:
- Use natural, conversational language
- Be encouraging and supportive
- Hindi should be in Devanagari script
- Focus on practical benefits
- Keep explanations concise but informative
- Return ONLY valid JSON, no markdown
"""

    def generate_explanations_batch(
        self,
        matches: list[tuple[HousingUnit, RankingScore, float, str]],
    ) -> dict[str, GeminiExplanation]:
        """
        Generate explanations for multiple matches.
        
        Args:
            matches: List of (unit, score, distance_km, eligibility_reason) tuples
        
        Returns:
            Dictionary mapping unit_id to explanation
        """
        explanations = {}
        
        for unit, score, distance_km, eligibility_reason in matches:
            try:
                explanation = self.generate_explanation(
                    unit,
                    score,
                    distance_km,
                    eligibility_reason,
                )
                explanations[unit.unitId] = explanation
            except Exception as exc:
                logger.error(
                    "explanation_generation_failed",
                    unit_id=unit.unitId,
                    error=str(exc),
                )
                # Create fallback explanation
                explanations[unit.unitId] = self._create_fallback_explanation(
                    unit,
                    score,
                    distance_km,
                )
        
        logger.info("explanations_generated", count=len(explanations))
        
        return explanations

    def _create_fallback_explanation(
        self,
        unit: HousingUnit,
        score: RankingScore,
        distance_km: float,
    ) -> GeminiExplanation:
        """Create fallback explanation when Gemini fails."""
        return GeminiExplanation(
            englishExplanation=(
                f"This {unit.scheme} housing unit is a good match for your family. "
                f"It is located {distance_km} km from your location and is priced at ₹{unit.priceINR:,}. "
                f"The unit can accommodate {unit.capacity} people, making it suitable for your family of {self.citizen.familySize}. "
                f"With an overall match score of {score.totalScore}/100, this unit offers good value and accessibility."
            ),
            hindiExplanation=(
                f"यह {unit.scheme} आवास इकाई आपके परिवार के लिए एक अच्छा विकल्प है। "
                f"यह आपके स्थान से {distance_km} किमी दूर है और इसकी कीमत ₹{unit.priceINR:,} है। "
                f"यह इकाई {unit.capacity} लोगों को समायोजित कर सकती है, जो आपके {self.citizen.familySize} सदस्यों के परिवार के लिए उपयुक्त है। "
                f"{score.totalScore}/100 के समग्र मैच स्कोर के साथ, यह इकाई अच्छा मूल्य और पहुंच प्रदान करती है।"
            ),
            eligibilityReason=(
                f"You are eligible because your monthly income of ₹{self.citizen.monthlyIncome:,} "
                f"is within the scheme limit of ₹{unit.maxIncome:,}, and your family size of "
                f"{self.citizen.familySize} fits the unit capacity of {unit.capacity}."
            ),
            documentChecklist=[
                "Aadhaar card (original and photocopy)",
                "Income certificate (issued within last 6 months)",
                "Ration card",
                "Domicile certificate",
                "Passport size photographs (4 copies)",
                "Bank account details",
                "Caste certificate (if applicable)",
            ],
            nextSteps=[
                "Visit the nearest housing office with all required documents",
                "Fill out the application form completely",
                "Submit documents for verification",
                "Pay the application fee (if applicable)",
                "Wait for verification and allotment notification",
            ],
        )

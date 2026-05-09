"""Ward analyzer orchestration service."""

from __future__ import annotations

from app.shared.logging.logger import get_logger
from app.ward_analyzer.infrastructure_scorer import (
    VisionScoringError,
    score_infrastructure_from_satellite,
)
from app.ward_analyzer.remediation_generator import (
    RemediationGenerationError,
    generate_remediation_plan,
)
from app.ward_analyzer.report_builder import build_ward_report
from app.ward_analyzer.satellite_fetcher import SatelliteImageError, validate_satellite_image

logger = get_logger(__name__)


class WardAnalysisError(Exception):
    """Raised when ward analysis pipeline fails."""


def analyze_ward(
    *,
    satellite_image_bytes: bytes,
    satellite_content_type: str,
    ward_name: str,
    population: int,
    city: str,
    state: str,
) -> dict:
    """Run full ward analysis pipeline with two sequential Gemini calls."""
    logger.info("ward_analysis_started", ward=ward_name, city=city, state=state)

    try:
        image_bytes, mime_type = validate_satellite_image(
            image_bytes=satellite_image_bytes,
            content_type=satellite_content_type,
        )

        vision_payload = score_infrastructure_from_satellite(
            image_bytes=image_bytes,
            mime_type=mime_type,
        )
        logger.info("vision_analysis_completed", ward=ward_name, confidence=vision_payload.confidence)

        remediation_payload = generate_remediation_plan(
            ward_name=ward_name,
            city=city,
            state=state,
            population=population,
            scores_payload=vision_payload,
        )
        logger.info("remediation_generated", ward=ward_name, budget_inr=remediation_payload.estimatedBudgetINR)

        report = build_ward_report(
            ward_name=ward_name,
            city=city,
            state=state,
            population=population,
            scores_payload=vision_payload,
            remediation_payload=remediation_payload,
        )
        logger.info("report_completed", ward=ward_name)
        return report
    except (SatelliteImageError, VisionScoringError, RemediationGenerationError) as exc:
        raise WardAnalysisError(str(exc)) from exc
    except Exception as exc:
        raise WardAnalysisError(f"Ward analysis failed unexpectedly: {exc}") from exc

"""
Complaint classifier service.

Classifies urban complaints into categories, severity, and departments.
"""

from app.shared.gemini.structured_output import generate_structured_output
from app.shared.prompts.complaint_classifier import get_complaint_classifier_prompt
from app.shared.schemas.complaint import ComplaintSchema
from app.shared.logging.logger import get_logger


logger = get_logger(__name__)


class ComplaintClassifierService:
    """Classifies complaints using Gemini AI."""

    @staticmethod
    def classify(complaint_text: str) -> ComplaintSchema:
        """
        Classify a complaint.

        Args:
            complaint_text: The complaint to classify

        Returns:
            Validated ComplaintSchema

        Raises:
            ValueError: If classification fails
        """
        try:
            prompt = get_complaint_classifier_prompt(complaint_text)
            result = generate_structured_output(
                prompt=prompt,
                schema=ComplaintSchema,
            )
            logger.info(
                "Complaint classified",
                category=result.category.value,
                severity=result.severity.value,
                confidence=result.confidence,
            )
            return result
        except Exception as e:
            logger.error(
                "Classification failed",
                error=str(e),
            )
            raise


def classify_complaint(complaint_text: str) -> ComplaintSchema:
    """Convenience function to classify a complaint."""
    return ComplaintClassifierService.classify(complaint_text)

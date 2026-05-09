"""Firestore update helpers for complaint classifier."""

from __future__ import annotations

from firebase_admin import firestore

from app.complaint_classifier.schemas import ClassificationResult


def build_success_update_payload(result: ClassificationResult) -> dict:
    """Build Firestore update payload for successful classification."""
    return {
        "aiProcessed": True,
        "status": "classified",
        "processingLock": False,
        "classifiedAt": firestore.SERVER_TIMESTAMP,
        "ai": {
            "category": result.category.value,
            "severity": result.severity.value,
            "department": result.department,
            "confidence": result.confidence,
            "summary": result.summary,
            "tags": result.tags,
            "needsHumanReview": result.needsHumanReview,
            "model": "gemini-2.5-flash",
        },
    }


def build_failure_update_payload(error_message: str) -> dict:
    """Build Firestore update payload for classification failure."""
    return {
        "aiProcessed": True,
        "status": "failed",
        "processingLock": False,
        "classifiedAt": firestore.SERVER_TIMESTAMP,
        "aiError": error_message[:500],
    }

"""Core complaint classification service orchestration."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

import requests
from fastapi import HTTPException, UploadFile, status
from firebase_admin import firestore
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.complaint_classifier.classifier import classify_from_image_and_text
from app.complaint_classifier.firestore_updater import (
    build_failure_update_payload,
    build_success_update_payload,
)
from app.complaint_classifier.schemas import ClassificationResult
from app.complaint_classifier.validator import FALLBACK_RESULT
from app.shared.firestore.client import get_firestore_client, get_storage_bucket
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024
COLLECTION_NAME = "complaints"


class ComplaintServiceError(Exception):
    """Base service exception."""


def _validate_image(content_type: str, image_bytes: bytes) -> str:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Allowed: jpg, jpeg, png, webp",
        )
    if len(image_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image file")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds 10MB limit",
        )
    return ALLOWED_CONTENT_TYPES[content_type]


async def upload_image_to_storage(image: UploadFile) -> tuple[str, str]:
    """Upload complaint image to Firebase Storage and return (url, object_path)."""
    image_bytes = await image.read()
    extension = _validate_image(image.content_type or "", image_bytes)

    object_path = f"complaints/{uuid.uuid4().hex}{extension}"
    bucket = get_storage_bucket()
    blob = bucket.blob(object_path)
    blob.upload_from_string(image_bytes, content_type=image.content_type)

    try:
        image_url = blob.generate_signed_url(version="v4", expiration=timedelta(days=7), method="GET")
    except Exception:
        image_url = f"https://storage.googleapis.com/{bucket.name}/{object_path}"
    return image_url, object_path


def create_complaint_document(
    *,
    description: str,
    image_url: str,
    latitude: float,
    longitude: float,
    address: str,
    user_id: str,
    storage_path: str,
) -> str:
    """Create initial complaint document and return complaint id."""
    db = get_firestore_client()
    ref = db.collection(COLLECTION_NAME).document()
    ref.set(
        {
            "description": description.strip(),
            "imageUrl": image_url,
            "storagePath": storage_path,
            "latitude": latitude,
            "longitude": longitude,
            "address": address.strip(),
            "userId": user_id.strip(),
            "status": "processing",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "aiProcessed": False,
            "processingLock": False,
        }
    )
    return ref.id


def _claim_processing_lock(complaint_id: str) -> bool:
    db = get_firestore_client()
    ref = db.collection(COLLECTION_NAME).document(complaint_id)
    transaction = db.transaction()

    @firestore.transactional
    def _txn_claim(txn):
        snapshot = ref.get(transaction=txn)
        if not snapshot.exists:
            return False
        data = snapshot.to_dict() or {}
        if data.get("aiProcessed") is True or data.get("processingLock") is True:
            return False
        txn.update(ref, {"processingLock": True})
        return True

    return bool(_txn_claim(transaction))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((requests.RequestException, TimeoutError, ConnectionError)),
    reraise=True,
)
def _download_image_bytes(image_url: str) -> tuple[bytes, str]:
    response = requests.get(image_url, timeout=25)
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip().lower()
    return response.content, mime_type


def _fetch_complaint_document(complaint_id: str) -> dict[str, Any]:
    db = get_firestore_client()
    doc = db.collection(COLLECTION_NAME).document(complaint_id).get()
    if not doc.exists:
        raise ComplaintServiceError(f"Complaint not found: {complaint_id}")
    return doc.to_dict() or {}


def _store_classification_result(complaint_id: str, result: ClassificationResult) -> None:
    db = get_firestore_client()
    ref = db.collection(COLLECTION_NAME).document(complaint_id)
    ref.update(build_success_update_payload(result))


def _store_failure_result(complaint_id: str, error_message: str) -> None:
    db = get_firestore_client()
    ref = db.collection(COLLECTION_NAME).document(complaint_id)
    ref.update(build_failure_update_payload(error_message))


def process_complaint_document(complaint_id: str) -> None:
    """Process complaint end-to-end and update Firestore."""
    logger.info("classification_started", complaint_id=complaint_id)

    if not _claim_processing_lock(complaint_id):
        return

    try:
        complaint = _fetch_complaint_document(complaint_id)
        image_url = str(complaint.get("imageUrl", "")).strip()
        description = str(complaint.get("description", "")).strip()
        if not image_url or not description:
            raise ComplaintServiceError("Complaint missing required imageUrl or description")

        image_bytes, mime_type = _download_image_bytes(image_url)
        result = classify_from_image_and_text(
            image_bytes=image_bytes,
            mime_type=mime_type,
            description=description,
        )
        _store_classification_result(complaint_id, result)
        logger.info(
            "classification_success",
            complaint_id=complaint_id,
            category=result.category.value,
            severity=result.severity.value,
        )
        logger.info("confidence_score", complaint_id=complaint_id, confidence=result.confidence)
    except Exception as exc:
        logger.error("classification_failed", complaint_id=complaint_id, error=str(exc))
        try:
            _store_classification_result(complaint_id, FALLBACK_RESULT)
        except Exception:
            _store_failure_result(complaint_id, str(exc))

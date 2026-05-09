"""Handle complaint submission via WhatsApp."""

from __future__ import annotations

import os
import uuid
from datetime import timedelta

import requests
from firebase_admin import firestore
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.complaint_classifier.service import process_complaint_document
from app.shared.firestore.client import get_firestore_client, get_storage_bucket
from app.shared.logging.logger import get_logger
from app.whatsapp_agent.schemas import ComplaintAcknowledgment

logger = get_logger(__name__)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


class ComplaintHandlerError(Exception):
    """Raised when complaint handling fails."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((requests.RequestException, TimeoutError)),
    reraise=True,
)
def download_whatsapp_media(media_url: str) -> tuple[bytes, str]:
    """Download media from WhatsApp/Twilio."""
    # Twilio requires authentication
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    
    if not account_sid or not auth_token:
        raise ComplaintHandlerError("Twilio credentials not configured")
    
    response = requests.get(
        media_url,
        auth=(account_sid, auth_token),
        timeout=30,
    )
    response.raise_for_status()
    
    content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip().lower()
    
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ComplaintHandlerError(f"Unsupported media type: {content_type}")
    
    return response.content, content_type


def upload_image_to_storage(image_bytes: bytes, content_type: str) -> tuple[str, str]:
    """Upload image to Firebase Storage."""
    extension_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    
    extension = extension_map.get(content_type, ".jpg")
    object_path = f"complaints/whatsapp/{uuid.uuid4().hex}{extension}"
    
    bucket = get_storage_bucket()
    blob = bucket.blob(object_path)
    blob.upload_from_string(image_bytes, content_type=content_type)
    
    try:
        image_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),
            method="GET",
        )
    except Exception:
        image_url = f"https://storage.googleapis.com/{bucket.name}/{object_path}"
    
    logger.info("image_uploaded", storage_path=object_path)
    
    return image_url, object_path


def create_complaint(
    description: str,
    image_url: str,
    storage_path: str,
    phone_number: str,
    latitude: float = 0.0,
    longitude: float = 0.0,
    address: str = "Location not provided",
) -> str:
    """Create complaint document in Firestore."""
    db = get_firestore_client()
    ref = db.collection("complaints").document()
    
    ref.set({
        "description": description.strip(),
        "imageUrl": image_url,
        "storagePath": storage_path,
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
        "userId": phone_number,
        "source": "whatsapp",
        "status": "processing",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "aiProcessed": False,
        "processingLock": False,
    })
    
    complaint_id = ref.id
    
    logger.info(
        "complaint_created",
        complaint_id=complaint_id,
        phone=phone_number,
        source="whatsapp",
    )
    
    return complaint_id


def process_complaint_async(complaint_id: str) -> None:
    """Trigger async complaint processing."""
    try:
        # This will be picked up by the complaint classifier
        process_complaint_document(complaint_id)
    except Exception as exc:
        logger.error("complaint_processing_failed", complaint_id=complaint_id, error=str(exc))


def handle_complaint_submission(
    description: str,
    media_url: str,
    phone_number: str,
) -> ComplaintAcknowledgment:
    """Handle complete complaint submission flow."""
    logger.info("complaint_submission_started", phone=phone_number)
    
    try:
        # Download image from WhatsApp
        image_bytes, content_type = download_whatsapp_media(media_url)
        
        # Upload to Firebase Storage
        image_url, storage_path = upload_image_to_storage(image_bytes, content_type)
        
        # Create complaint document
        complaint_id = create_complaint(
            description=description,
            image_url=image_url,
            storage_path=storage_path,
            phone_number=phone_number,
        )
        
        # Trigger async processing
        process_complaint_async(complaint_id)
        
        # Return acknowledgment
        return ComplaintAcknowledgment(
            complaintId=complaint_id,
            category="Processing",
            severity="Pending",
            estimatedResolutionDays=7,
            assignedDepartment="Municipal Services",
            message=f"Complaint registered successfully! Your complaint ID is: {complaint_id[:8]}...\n\nWe will process your complaint and assign it to the appropriate department within 24 hours.",
        )
    
    except Exception as exc:
        logger.error("complaint_submission_failed", phone=phone_number, error=str(exc))
        raise ComplaintHandlerError(f"Failed to submit complaint: {exc}") from exc


def handle_text_only_complaint(description: str, phone_number: str) -> str:
    """Handle complaint without image."""
    return (
        "To file a complaint, please send:\n"
        "1. A photo of the issue\n"
        "2. A description of the problem\n\n"
        "Example: Send a photo of the broken road with text 'Road broken near school'"
    )

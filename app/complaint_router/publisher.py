"""Routing event publisher with Firestore persistence."""

from __future__ import annotations

from typing import Any

from firebase_admin import firestore

from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)
ROUTING_EVENTS_COLLECTION = "routing_events"


def publish_routing_event(event_payload: dict[str, Any]) -> str | None:
    """Publish routing event to Firestore for audit and future Pub/Sub bridge."""
    db = get_firestore_client()
    payload = {
        **event_payload,
        "publishedAt": firestore.SERVER_TIMESTAMP,
    }
    try:
        ref = db.collection(ROUTING_EVENTS_COLLECTION).document()
        ref.set(payload)
        return ref.id
    except Exception as exc:
        logger.error("routing_event_publish_failed", error=str(exc), event=event_payload.get("event"))
        return None

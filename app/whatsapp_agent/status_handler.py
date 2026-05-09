"""Handle complaint status tracking."""

from __future__ import annotations

from typing import Optional

from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger
from app.whatsapp_agent.schemas import StatusUpdate

logger = get_logger(__name__)


class StatusHandlerError(Exception):
    """Raised when status handling fails."""


def fetch_complaint_status(complaint_id: str) -> Optional[dict]:
    """Fetch complaint from Firestore."""
    db = get_firestore_client()
    doc = db.collection("complaints").document(complaint_id).get()
    
    if not doc.exists:
        return None
    
    return doc.to_dict()


def fetch_routing_status(complaint_id: str) -> Optional[dict]:
    """Fetch routing status from routing_events collection."""
    db = get_firestore_client()
    
    # Query routing events for this complaint
    query = (
        db.collection("routing_events")
        .where("complaintId", "==", complaint_id)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    
    docs = list(query.stream())
    if docs:
        return docs[0].to_dict()
    
    return None


def fetch_escalation_status(complaint_id: str) -> Optional[dict]:
    """Fetch escalation status if exists."""
    db = get_firestore_client()
    
    # Query escalations for this complaint
    query = (
        db.collection("escalations")
        .where("complaintId", "==", complaint_id)
        .order_by("escalatedAt", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    
    docs = list(query.stream())
    if docs:
        return docs[0].to_dict()
    
    return None


def handle_status_request(complaint_id: str) -> StatusUpdate:
    """Handle complaint status request."""
    logger.info("status_request", complaint_id=complaint_id)
    
    # Fetch complaint
    complaint = fetch_complaint_status(complaint_id)
    
    if not complaint:
        raise StatusHandlerError(f"Complaint not found: {complaint_id}")
    
    # Fetch routing status
    routing = fetch_routing_status(complaint_id)
    
    # Fetch escalation status
    escalation = fetch_escalation_status(complaint_id)
    
    # Build status message
    status = complaint.get("status", "processing")
    category = complaint.get("category", "Unknown")
    severity = complaint.get("severity", "Unknown")
    
    assigned_officer = None
    if routing:
        assigned_officer = routing.get("assignedOfficer", {}).get("name")
    
    escalation_level = None
    if escalation:
        escalation_level = escalation.get("escalationLevel", "Level 1")
    
    # Format last update time
    created_at = complaint.get("createdAt")
    if created_at:
        last_update = created_at.strftime("%Y-%m-%d %H:%M") if hasattr(created_at, "strftime") else str(created_at)
    else:
        last_update = "Recently"
    
    # Build message
    message_parts = [
        f"📋 Complaint Status: {complaint_id[:8]}...",
        f"",
        f"Status: {status.upper()}",
        f"Category: {category}",
        f"Severity: {severity}",
    ]
    
    if assigned_officer:
        message_parts.append(f"Assigned to: {assigned_officer}")
    
    if escalation_level:
        message_parts.append(f"⚠️ Escalation: {escalation_level}")
    
    message_parts.extend([
        f"",
        f"Last updated: {last_update}",
    ])
    
    # Add status-specific messages
    if status == "processing":
        message_parts.append("\n⏳ Your complaint is being processed. We'll update you soon.")
    elif status == "assigned":
        message_parts.append("\n✅ Your complaint has been assigned to an officer.")
    elif status == "in_progress":
        message_parts.append("\n🔧 Work is in progress on your complaint.")
    elif status == "resolved":
        message_parts.append("\n✅ Your complaint has been resolved!")
    elif status == "closed":
        message_parts.append("\n✅ Your complaint has been closed.")
    
    message = "\n".join(message_parts)
    
    return StatusUpdate(
        complaintId=complaint_id,
        status=status,
        assignedOfficer=assigned_officer,
        lastUpdate=last_update,
        escalationLevel=escalation_level,
        message=message,
    )


def handle_status_not_found(complaint_id: str) -> str:
    """Handle case when complaint is not found."""
    return (
        f"❌ Complaint not found: {complaint_id}\n\n"
        "Please check the complaint ID and try again.\n"
        "You can find your complaint ID in the acknowledgment message we sent when you filed the complaint."
    )

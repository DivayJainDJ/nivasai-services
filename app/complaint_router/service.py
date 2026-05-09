"""End-to-end complaint routing orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from firebase_admin import firestore

from app.complaint_router.escalation_checker import evaluate_escalation
from app.complaint_router.officer_selector import select_officer_for_department
from app.complaint_router.publisher import publish_routing_event
from app.complaint_router.routing_engine import generate_routing_decision
from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)
COMPLAINTS_COLLECTION = "complaints"


@dataclass(frozen=True)
class RoutingResult:
    success: bool
    complaintId: str
    routingStatus: str
    department: str | None = None
    assignedOfficer: str | None = None
    priority: str | None = None
    escalated: bool = False
    message: str | None = None


class ComplaintRoutingError(Exception):
    """Raised for complaint routing failures."""


def _read_complaint(complaint_id: str) -> dict[str, Any]:
    db = get_firestore_client()
    doc = db.collection(COMPLAINTS_COLLECTION).document(complaint_id).get()
    if not doc.exists:
        raise ComplaintRoutingError(f"Complaint not found: {complaint_id}")
    data = doc.to_dict() or {}
    data["_id"] = doc.id
    return data


def _validate_ai_data(data: dict[str, Any]) -> dict[str, Any]:
    ai = data.get("ai")
    if not isinstance(ai, dict):
        raise ComplaintRoutingError("Missing AI classification payload")
    for required in ("category", "severity", "department", "confidence"):
        if required not in ai:
            raise ComplaintRoutingError(f"Missing AI field: {required}")
    return ai


def _update_officer_load(officer_id: str) -> None:
    db = get_firestore_client()
    query = db.collection("officers").where("officerId", "==", officer_id).limit(1)
    docs = list(query.stream())
    if not docs:
        return
    doc_ref = docs[0].reference
    current = int((docs[0].to_dict() or {}).get("currentLoad", 0))
    doc_ref.update({"currentLoad": current + 1, "lastAssignedAt": firestore.SERVER_TIMESTAMP})


def _persist_routing(
    *,
    complaint_id: str,
    routing_update: dict[str, Any],
    escalation_update: dict[str, Any],
) -> None:
    db = get_firestore_client()
    ref = db.collection(COMPLAINTS_COLLECTION).document(complaint_id)
    ref.update(
        {
            "routing": routing_update,
            "escalation": escalation_update,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
    )


def route_complaint_by_id(complaint_id: str) -> RoutingResult:
    """Route a classified complaint and persist assignment metadata."""
    logger.info("routing_started", complaint_id=complaint_id)
    try:
        complaint = _read_complaint(complaint_id)
        ai = _validate_ai_data(complaint)

        decision = generate_routing_decision(
            department=str(ai["department"]),
            severity=str(ai["severity"]),
        )

        officer = select_officer_for_department(
            department=decision.department,
            complaint_lat=float(complaint.get("latitude")) if complaint.get("latitude") is not None else None,
            complaint_lng=float(complaint.get("longitude")) if complaint.get("longitude") is not None else None,
            complaint_zone=str(complaint.get("zone", "")).strip() or None,
        )
        if officer is None:
            raise ComplaintRoutingError(f"No available officer for department: {decision.department}")

        logger.info(
            "officer_selected",
            complaint_id=complaint_id,
            officer_id=officer.officerId,
            department=officer.department,
            current_load=officer.currentLoad,
            distance_km=officer.distanceKm,
        )

        escalation = evaluate_escalation(
            severity=str(ai["severity"]),
            confidence=float(ai.get("confidence", 0.0)),
            description=str(complaint.get("description", "")),
            created_at=complaint.get("createdAt"),
            status=str(complaint.get("status", "open")),
        )
        if escalation.escalated:
            logger.warning(
                "escalation_triggered",
                complaint_id=complaint_id,
                escalation_level=escalation.escalationLevel,
                reasons=escalation.escalationReasons,
            )

        routing_status = "assigned"
        routing_update = {
            "department": decision.department,
            "priority": decision.priority,
            "urgency": decision.urgency,
            "dispatchLevel": decision.dispatchLevel,
            "assignedOfficer": officer.officerId,
            "routingStatus": routing_status,
            "assignedAt": firestore.SERVER_TIMESTAMP,
            "escalated": escalation.escalated,
        }
        escalation_update = {
            "escalated": escalation.escalated,
            "escalationLevel": escalation.escalationLevel,
            "reasons": escalation.escalationReasons,
            "slaBreached": escalation.slaBreached,
            "emergencyRouting": escalation.emergencyRouting,
        }

        _persist_routing(
            complaint_id=complaint_id,
            routing_update=routing_update,
            escalation_update=escalation_update,
        )
        _update_officer_load(officer.officerId)
        logger.info("firestore_updated", complaint_id=complaint_id)

        publish_routing_event(
            {
                "event": "complaint_assigned",
                "complaintId": complaint_id,
                "officerId": officer.officerId,
                "department": decision.department,
                "priority": decision.priority,
                "routingStatus": routing_status,
                "escalated": escalation.escalated,
            }
        )

        logger.info("routing_completed", complaint_id=complaint_id, routing_status=routing_status)
        return RoutingResult(
            success=True,
            complaintId=complaint_id,
            routingStatus=routing_status,
            department=decision.department,
            assignedOfficer=officer.officerId,
            priority=decision.priority,
            escalated=escalation.escalated,
        )
    except ComplaintRoutingError as exc:
        logger.error("routing_failed", complaint_id=complaint_id, error=str(exc))
        return RoutingResult(
            success=False,
            complaintId=complaint_id,
            routingStatus="failed",
            message=str(exc),
        )
    except Exception as exc:
        logger.error("routing_failed", complaint_id=complaint_id, error=str(exc))
        return RoutingResult(
            success=False,
            complaintId=complaint_id,
            routingStatus="failed",
            message="Unexpected routing error",
        )

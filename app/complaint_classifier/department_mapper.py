"""Department mapping for complaint categories."""

from __future__ import annotations

from app.complaint_classifier.schemas import ComplaintCategory


DEPARTMENT_MAP: dict[ComplaintCategory, str] = {
    ComplaintCategory.ROAD_DAMAGE: "Roads & Infrastructure",
    ComplaintCategory.GARBAGE: "Sanitation",
    ComplaintCategory.DRAINAGE: "Public Works",
    ComplaintCategory.WATER_LEAKAGE: "Water Department",
    ComplaintCategory.STREETLIGHT_ISSUE: "Electricity Board",
    ComplaintCategory.ELECTRICAL_HAZARD: "Electricity Board",
    ComplaintCategory.TRAFFIC_ISSUE: "Traffic Police",
    ComplaintCategory.ILLEGAL_DUMPING: "Sanitation",
    ComplaintCategory.PUBLIC_SAFETY: "Emergency Response",
    ComplaintCategory.SEWAGE: "Public Works",
    ComplaintCategory.FLOODING: "Disaster Management",
    ComplaintCategory.OTHER: "Manual Review",
}


def map_department(category: ComplaintCategory) -> str:
    """Return responsible department for category."""
    return DEPARTMENT_MAP.get(category, "Manual Review")

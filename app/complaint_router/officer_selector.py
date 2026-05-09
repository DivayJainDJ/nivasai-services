"""Officer selection logic for complaint routing."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.shared.firestore.client import get_firestore_client

OFFICERS_COLLECTION = "officers"


@dataclass(frozen=True)
class OfficerSelectionResult:
    officerId: str
    department: str
    zone: str
    currentLoad: int
    distanceKm: float | None


def _distance_km(
    complaint_lat: float | None,
    complaint_lng: float | None,
    officer_lat: float | None,
    officer_lng: float | None,
) -> float | None:
    if None in (complaint_lat, complaint_lng, officer_lat, officer_lng):
        return None
    r = 6371.0
    dlat = math.radians(officer_lat - complaint_lat)
    dlng = math.radians(officer_lng - complaint_lng)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(complaint_lat))
        * math.cos(math.radians(officer_lat))
        * math.sin(dlng / 2) ** 2
    )
    return r * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _normalize_zone(data: dict[str, Any]) -> str:
    return str(data.get("zone", "unknown")).strip().lower()


def _extract_officer_id(doc_id: str, data: dict[str, Any]) -> str:
    raw = str(data.get("officerId", "")).strip()
    return raw if raw else doc_id


def select_officer_for_department(
    *,
    department: str,
    complaint_lat: float | None,
    complaint_lng: float | None,
    complaint_zone: str | None = None,
) -> OfficerSelectionResult | None:
    """Select active officer by department, nearest, and least current load."""
    db = get_firestore_client()
    query = (
        db.collection(OFFICERS_COLLECTION)
        .where("department", "==", department)
        .where("active", "==", True)
    )

    officers: list[tuple[str, dict[str, Any]]] = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        officers.append((doc.id, data))

    if not officers:
        return None

    zone_filter = (complaint_zone or "").strip().lower()
    if zone_filter:
        zone_matched = [(doc_id, data) for doc_id, data in officers if _normalize_zone(data) == zone_filter]
        if zone_matched:
            officers = zone_matched

    ranked: list[tuple[int, float, str, dict[str, Any]]] = []
    for doc_id, data in officers:
        load = int(data.get("currentLoad", 0))
        dist = _distance_km(
            complaint_lat=complaint_lat,
            complaint_lng=complaint_lng,
            officer_lat=float(data["latitude"]) if data.get("latitude") is not None else None,
            officer_lng=float(data["longitude"]) if data.get("longitude") is not None else None,
        )
        distance_rank = dist if dist is not None else 1e9
        ranked.append((load, distance_rank, doc_id, data))

    ranked.sort(key=lambda item: (item[0], item[1]))
    load, dist, doc_id, data = ranked[0]
    return OfficerSelectionResult(
        officerId=_extract_officer_id(doc_id, data),
        department=str(data.get("department", department)),
        zone=str(data.get("zone", "unknown")),
        currentLoad=load,
        distanceKm=None if dist == 1e9 else round(dist, 3),
    )

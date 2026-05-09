from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest


class FakeDocSnapshot:
    def __init__(self, doc_id: str, data: dict[str, Any] | None, reference: "FakeDocRef"):
        self.id = doc_id
        self._data = deepcopy(data) if data is not None else None
        self.reference = reference

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return deepcopy(self._data) if self._data is not None else None


class FakeDocRef:
    def __init__(self, collection: "FakeCollectionRef", doc_id: str):
        self._collection = collection
        self.id = doc_id

    def get(self, transaction=None) -> FakeDocSnapshot:
        del transaction
        data = self._collection._docs.get(self.id)
        return FakeDocSnapshot(self.id, data, self)

    def set(self, payload: dict[str, Any]) -> None:
        self._collection._docs[self.id] = deepcopy(payload)

    def update(self, payload: dict[str, Any]) -> None:
        if self.id not in self._collection._docs:
            self._collection._docs[self.id] = {}
        self._collection._docs[self.id].update(deepcopy(payload))


class FakeQuery:
    def __init__(self, collection: "FakeCollectionRef", predicates: list[tuple[str, str, Any]] | None = None):
        self._collection = collection
        self._predicates = predicates or []
        self._limit: int | None = None

    def where(self, field: str, op: str, value: Any) -> "FakeQuery":
        return FakeQuery(self._collection, [*self._predicates, (field, op, value)])

    def limit(self, n: int) -> "FakeQuery":
        q = FakeQuery(self._collection, list(self._predicates))
        q._limit = n
        return q

    def stream(self):
        docs: list[FakeDocSnapshot] = []
        for doc_id, data in self._collection._docs.items():
            ok = True
            for field, op, value in self._predicates:
                if op != "==":
                    raise ValueError("FakeQuery supports only == operator")
                if data.get(field) != value:
                    ok = False
                    break
            if ok:
                docs.append(FakeDocSnapshot(doc_id, data, FakeDocRef(self._collection, doc_id)))
        if self._limit is not None:
            docs = docs[: self._limit]
        return docs


class FakeCollectionRef:
    def __init__(self, name: str, docs: dict[str, dict[str, Any]]):
        self.name = name
        self._docs = docs

    def document(self, doc_id: str | None = None) -> FakeDocRef:
        if doc_id is None:
            doc_id = f"auto_{len(self._docs) + 1}"
        return FakeDocRef(self, doc_id)

    def where(self, field: str, op: str, value: Any) -> FakeQuery:
        return FakeQuery(self, [(field, op, value)])

    def stream(self):
        return [FakeDocSnapshot(doc_id, data, FakeDocRef(self, doc_id)) for doc_id, data in self._docs.items()]


class FakeFirestoreClient:
    def __init__(self, seed_data: dict[str, dict[str, dict[str, Any]]]):
        self._collections = {name: deepcopy(docs) for name, docs in seed_data.items()}

    def collection(self, name: str) -> FakeCollectionRef:
        if name not in self._collections:
            self._collections[name] = {}
        return FakeCollectionRef(name, self._collections[name])

    def dump(self) -> dict[str, dict[str, dict[str, Any]]]:
        return deepcopy(self._collections)


@dataclass
class LogCall:
    level: str
    message: str
    payload: dict[str, Any]


class FakeLogger:
    def __init__(self):
        self.calls: list[LogCall] = []

    def info(self, message: str, **kwargs):
        self.calls.append(LogCall("info", message, kwargs))

    def warning(self, message: str, **kwargs):
        self.calls.append(LogCall("warning", message, kwargs))

    def error(self, message: str, **kwargs):
        self.calls.append(LogCall("error", message, kwargs))


@pytest.fixture
def officer_seed_data() -> dict[str, dict[str, Any]]:
    return {
        "officer_road_1": {
            "officerId": "officer_road_1",
            "department": "Roads & Infrastructure",
            "zone": "south",
            "active": True,
            "currentLoad": 4,
            "latitude": 12.9710,
            "longitude": 77.5940,
        },
        "officer_road_2": {
            "officerId": "officer_road_2",
            "department": "Roads & Infrastructure",
            "zone": "south",
            "active": True,
            "currentLoad": 1,
            "latitude": 12.9720,
            "longitude": 77.5950,
        },
        "officer_elec_1": {
            "officerId": "officer_elec_1",
            "department": "Electricity Board",
            "zone": "south",
            "active": True,
            "currentLoad": 2,
            "latitude": 12.9750,
            "longitude": 77.6000,
        },
        "officer_inactive": {
            "officerId": "officer_inactive",
            "department": "Roads & Infrastructure",
            "zone": "south",
            "active": False,
            "currentLoad": 0,
        },
    }


@pytest.fixture
def complaint_seed_data() -> dict[str, dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return {
        "cmp_pothole": {
            "description": "Large pothole near school crossing",
            "status": "open",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "zone": "south",
            "createdAt": now,
            "ai": {
                "category": "Road Damage",
                "severity": "high",
                "department": "Roads & Infrastructure",
                "confidence": 0.94,
                "summary": "Large pothole visible on roadway",
                "tags": ["pothole", "road-damage", "hazard"],
            },
        },
        "cmp_flooding": {
            "description": "Street flooding near bus stand",
            "status": "open",
            "latitude": 12.9730,
            "longitude": 77.5960,
            "zone": "south",
            "createdAt": now,
            "ai": {
                "category": "Flooding",
                "severity": "critical",
                "department": "Disaster Management",
                "confidence": 0.91,
                "summary": "Floodwater blocking street lanes",
                "tags": ["flooding", "waterlogging", "hazard"],
            },
        },
        "cmp_wire": {
            "description": "Exposed electric wire near hospital entrance",
            "status": "open",
            "createdAt": now,
            "ai": {
                "category": "Electrical Hazard",
                "severity": "critical",
                "department": "Electricity Board",
                "confidence": 0.97,
                "summary": "Live wire visible near pedestrian area",
                "tags": ["electrical", "hazard", "public-safety"],
            },
        },
        "cmp_garbage": {
            "description": "Garbage overflow with bad smell",
            "status": "open",
            "createdAt": now,
            "ai": {
                "category": "Garbage",
                "severity": "medium",
                "department": "Sanitation",
                "confidence": 0.88,
                "summary": "Overflowing garbage bins on street",
                "tags": ["garbage", "overflow", "sanitation"],
            },
        },
        "cmp_unclear": {
            "description": "Image unclear and complaint text vague",
            "status": "open",
            "createdAt": now - timedelta(hours=30),
            "ai": {
                "category": "Other",
                "severity": "low",
                "department": "Manual Review",
                "confidence": 0.34,
                "summary": "Unable to determine civic issue",
                "tags": ["manual-review", "unclear"],
            },
        },
    }


@pytest.fixture
def fake_db(officer_seed_data, complaint_seed_data) -> FakeFirestoreClient:
    return FakeFirestoreClient(
        {
            "officers": officer_seed_data,
            "complaints": complaint_seed_data,
            "routing_events": {},
        }
    )


@pytest.fixture
def patch_router_firestore(monkeypatch, fake_db):
    from app.complaint_router import officer_selector, publisher, service

    monkeypatch.setattr(officer_selector, "get_firestore_client", lambda: fake_db)
    monkeypatch.setattr(publisher, "get_firestore_client", lambda: fake_db)
    monkeypatch.setattr(service, "get_firestore_client", lambda: fake_db)
    return fake_db


@pytest.fixture
def fake_logger(monkeypatch):
    from app.complaint_router import publisher, service

    logger = FakeLogger()
    monkeypatch.setattr(service, "logger", logger)
    monkeypatch.setattr(publisher, "logger", logger)
    return logger

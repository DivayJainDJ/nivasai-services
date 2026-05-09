"""Routing engine for complaint assignment decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingDecision:
    department: str
    priority: str
    urgency: str
    dispatchLevel: str
    isEmergency: bool


def _priority_for_severity(severity: str) -> str:
    normalized = (severity or "").strip().lower()
    if normalized == "critical":
        return "emergency"
    if normalized == "high":
        return "urgent"
    if normalized == "medium":
        return "standard"
    return "low"


def _urgency_for_priority(priority: str) -> str:
    if priority == "emergency":
        return "immediate"
    if priority == "urgent":
        return "same-day"
    if priority == "standard":
        return "24-hours"
    return "72-hours"


def _dispatch_for_priority(priority: str) -> str:
    if priority == "emergency":
        return "rapid-response"
    if priority == "urgent":
        return "priority-queue"
    if priority == "standard":
        return "normal-queue"
    return "deferred-queue"


def generate_routing_decision(*, department: str, severity: str) -> RoutingDecision:
    """Generate routing decision from complaint classification."""
    priority = _priority_for_severity(severity)
    return RoutingDecision(
        department=department,
        priority=priority,
        urgency=_urgency_for_priority(priority),
        dispatchLevel=_dispatch_for_priority(priority),
        isEmergency=priority == "emergency",
    )

"""Pydantic schemas for analytics aggregator."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ComplaintMetrics(BaseModel):
    """Complaint aggregation metrics."""

    wardId: Optional[str] = None
    totalComplaints: int = 0
    complaintsByCategory: dict[str, int] = Field(default_factory=dict)
    complaintsBySeverity: dict[str, int] = Field(default_factory=dict)
    resolutionRate: float = 0.0
    averageResponseTimeHours: float = 0.0
    pendingComplaints: int = 0
    resolvedComplaints: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RoutingMetrics(BaseModel):
    """Routing aggregation metrics."""

    totalRoutings: int = 0
    officerWorkloads: dict[str, int] = Field(default_factory=dict)
    averageAssignmentLatencyMinutes: float = 0.0
    routingEfficiency: float = 0.0
    unresolvedBacklog: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EscalationMetrics(BaseModel):
    """Escalation aggregation metrics."""

    totalEscalations: int = 0
    slaBreaches: int = 0
    emergencyIncidents: int = 0
    criticalComplaintDensity: float = 0.0
    escalationRate: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WardMetrics(BaseModel):
    """Ward infrastructure metrics."""

    wardId: str
    roadQualityScore: float = Field(ge=0.0, le=100.0)
    sanitationScore: float = Field(ge=0.0, le=100.0)
    floodRiskScore: float = Field(ge=0.0, le=100.0)
    greenCoverageScore: float = Field(ge=0.0, le=100.0)
    overallInfrastructureScore: float = Field(ge=0.0, le=100.0)
    generatedAt: datetime = Field(default_factory=datetime.utcnow)


class AnomalyReport(BaseModel):
    """Anomaly detection report."""

    anomalyType: Literal[
        "complaint_spike",
        "escalation_surge",
        "officer_overload",
        "infrastructure_deterioration",
        "flood_risk_surge",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    wardId: Optional[str] = None
    description: str
    metricValue: float
    expectedValue: float
    deviationPercent: float
    detectedAt: datetime = Field(default_factory=datetime.utcnow)


class WardBrief(BaseModel):
    """AI-generated ward intelligence brief."""

    wardId: str
    summary: str
    majorIssues: list[str] = Field(default_factory=list)
    trendAnalysis: str
    riskAssessment: str
    priorityRecommendations: list[str] = Field(default_factory=list)
    citizenImpact: str
    generatedAt: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsSummary(BaseModel):
    """Overall analytics summary."""

    totalComplaints: int
    totalWards: int
    criticalIssues: int
    averageResolutionRate: float
    topIssueCategories: list[str]
    anomaliesDetected: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BigQueryRow(BaseModel):
    """Generic BigQuery row."""

    data: dict[str, Any]
    table: str


class AnalyticsJobResult(BaseModel):
    """Analytics job execution result."""

    jobId: str
    status: Literal["success", "partial", "failed"]
    complaintMetrics: Optional[ComplaintMetrics] = None
    routingMetrics: Optional[RoutingMetrics] = None
    escalationMetrics: Optional[EscalationMetrics] = None
    wardMetrics: list[WardMetrics] = Field(default_factory=list)
    anomalies: list[AnomalyReport] = Field(default_factory=list)
    wardBriefs: list[WardBrief] = Field(default_factory=list)
    executionTimeSeconds: float = 0.0
    errors: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

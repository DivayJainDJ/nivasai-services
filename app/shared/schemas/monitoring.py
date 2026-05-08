"""
Monitoring and analytics schema.
"""

from pydantic import BaseModel, Field
from typing import Dict, List
from enum import Enum


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class WardAlert(BaseModel):
    """Ward-level alert."""

    ward_id: str
    alert_level: AlertLevel
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: str


class MonitoringMetrics(BaseModel):
    """System monitoring metrics."""

    complaints_per_day: int
    resolution_rate: float
    avg_resolution_time_hours: int
    escalation_count: int
    pressure_score: float = Field(ge=0, le=100)

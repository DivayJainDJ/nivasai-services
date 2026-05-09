"""Escalation metrics aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.analytics_aggregator.schemas import EscalationMetrics
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class EscalationAggregator:
    """Aggregate escalation statistics."""

    def __init__(self):
        """Initialize escalation aggregator."""
        self.db = db

    def aggregate_escalations(self, hours: int = 24) -> EscalationMetrics:
        """
        Aggregate escalation metrics.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            EscalationMetrics with aggregated data
        """
        try:
            # Calculate time window
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Query complaints for escalation data
            complaints = []
            
            for doc in self.db.collection("complaints").stream():
                complaint_data = doc.to_dict()
                created_at = complaint_data.get("createdAt")
                
                if created_at and created_at >= cutoff_time:
                    complaints.append(complaint_data)
            
            # Count escalations
            escalated = [c for c in complaints if c.get("escalated", False)]
            total_escalations = len(escalated)
            
            # Count SLA breaches
            sla_breaches = sum(1 for c in complaints if c.get("slaBreached", False))
            
            # Count emergency incidents
            emergency = sum(
                1 for c in complaints
                if c.get("severity") == "critical" or c.get("priority") == "emergency"
            )
            
            # Calculate critical complaint density
            critical_complaints = sum(1 for c in complaints if c.get("severity") == "critical")
            total_complaints = len(complaints)
            
            critical_density = (
                (critical_complaints / total_complaints * 100)
                if total_complaints > 0
                else 0.0
            )
            
            # Calculate escalation rate
            escalation_rate = (
                (total_escalations / total_complaints * 100)
                if total_complaints > 0
                else 0.0
            )
            
            logger.info(
                "escalations_aggregated",
                total=total_escalations,
                sla_breaches=sla_breaches,
                emergency=emergency,
            )
            
            return EscalationMetrics(
                totalEscalations=total_escalations,
                slaBreaches=sla_breaches,
                emergencyIncidents=emergency,
                criticalComplaintDensity=round(critical_density, 2),
                escalationRate=round(escalation_rate, 2),
            )
        
        except Exception as exc:
            logger.error("escalation_aggregation_failed", error=str(exc))
            return EscalationMetrics()

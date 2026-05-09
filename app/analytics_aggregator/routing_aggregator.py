"""Routing metrics aggregation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from app.analytics_aggregator.schemas import RoutingMetrics
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class RoutingAggregator:
    """Aggregate routing statistics."""

    def __init__(self):
        """Initialize routing aggregator."""
        self.db = db

    def aggregate_routing(self, hours: int = 24) -> RoutingMetrics:
        """
        Aggregate routing metrics.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            RoutingMetrics with aggregated data
        """
        try:
            # Calculate time window
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Query routing events
            routing_events = []
            
            try:
                for doc in self.db.collection("routing_events").stream():
                    event_data = doc.to_dict()
                    created_at = event_data.get("createdAt")
                    
                    if created_at and created_at >= cutoff_time:
                        routing_events.append(event_data)
            except Exception:
                # Collection might not exist yet
                pass
            
            total_routings = len(routing_events)
            
            # Count officer workloads
            officer_workloads = defaultdict(int)
            for event in routing_events:
                officer_id = event.get("officerId")
                if officer_id:
                    officer_workloads[officer_id] += 1
            
            # Calculate assignment latency
            latencies = []
            for event in routing_events:
                created = event.get("createdAt")
                assigned = event.get("assignedAt")
                
                if created and assigned:
                    delta = assigned - created
                    latencies.append(delta.total_seconds() / 60)  # Convert to minutes
            
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            
            # Calculate routing efficiency
            successful = sum(1 for e in routing_events if e.get("status") == "assigned")
            efficiency = (successful / total_routings * 100) if total_routings > 0 else 0.0
            
            # Count unresolved backlog
            unresolved = sum(1 for e in routing_events if e.get("status") == "pending")
            
            logger.info(
                "routing_aggregated",
                total=total_routings,
                officers=len(officer_workloads),
                efficiency=efficiency,
            )
            
            return RoutingMetrics(
                totalRoutings=total_routings,
                officerWorkloads=dict(officer_workloads),
                averageAssignmentLatencyMinutes=round(avg_latency, 2),
                routingEfficiency=round(efficiency, 2),
                unresolvedBacklog=unresolved,
            )
        
        except Exception as exc:
            logger.error("routing_aggregation_failed", error=str(exc))
            return RoutingMetrics()

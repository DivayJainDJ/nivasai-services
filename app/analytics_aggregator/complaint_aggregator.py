"""Complaint metrics aggregation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from app.analytics_aggregator.schemas import ComplaintMetrics
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ComplaintAggregator:
    """Aggregate complaint statistics."""

    def __init__(self):
        """Initialize complaint aggregator."""
        self.db = db

    def aggregate_complaints(
        self,
        ward_id: Optional[str] = None,
        hours: int = 24,
    ) -> ComplaintMetrics:
        """
        Aggregate complaint metrics.
        
        Args:
            ward_id: Optional ward ID to filter by
            hours: Number of hours to look back
        
        Returns:
            ComplaintMetrics with aggregated data
        """
        try:
            # Calculate time window
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Query complaints
            query = self.db.collection("complaints")
            
            if ward_id:
                query = query.where("wardId", "==", ward_id)
            
            # Get complaints from time window
            complaints = []
            for doc in query.stream():
                complaint_data = doc.to_dict()
                created_at = complaint_data.get("createdAt")
                
                # Check if within time window
                if created_at and created_at >= cutoff_time:
                    complaints.append(complaint_data)
            
            # Aggregate metrics
            total_complaints = len(complaints)
            
            # Count by category
            by_category = defaultdict(int)
            for complaint in complaints:
                category = complaint.get("category", "unknown")
                by_category[category] += 1
            
            # Count by severity
            by_severity = defaultdict(int)
            for complaint in complaints:
                severity = complaint.get("severity", "medium")
                by_severity[severity] += 1
            
            # Calculate resolution metrics
            resolved = sum(1 for c in complaints if c.get("status") == "resolved")
            pending = sum(1 for c in complaints if c.get("status") in ["pending", "processing"])
            
            resolution_rate = (resolved / total_complaints * 100) if total_complaints > 0 else 0.0
            
            # Calculate average response time
            response_times = []
            for complaint in complaints:
                created = complaint.get("createdAt")
                resolved_at = complaint.get("resolvedAt")
                
                if created and resolved_at:
                    delta = resolved_at - created
                    response_times.append(delta.total_seconds() / 3600)  # Convert to hours
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            
            logger.info(
                "complaints_aggregated",
                ward_id=ward_id,
                total=total_complaints,
                resolved=resolved,
                pending=pending,
            )
            
            return ComplaintMetrics(
                wardId=ward_id,
                totalComplaints=total_complaints,
                complaintsByCategory=dict(by_category),
                complaintsBySeverity=dict(by_severity),
                resolutionRate=round(resolution_rate, 2),
                averageResponseTimeHours=round(avg_response_time, 2),
                pendingComplaints=pending,
                resolvedComplaints=resolved,
            )
        
        except Exception as exc:
            logger.error("complaint_aggregation_failed", error=str(exc))
            return ComplaintMetrics(wardId=ward_id)

    def aggregate_all_wards(self, hours: int = 24) -> dict[str, ComplaintMetrics]:
        """Aggregate complaints for all wards."""
        try:
            # Get unique ward IDs
            ward_ids = set()
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            for doc in self.db.collection("complaints").stream():
                complaint_data = doc.to_dict()
                created_at = complaint_data.get("createdAt")
                
                if created_at and created_at >= cutoff_time:
                    ward_id = complaint_data.get("wardId")
                    if ward_id:
                        ward_ids.add(ward_id)
            
            # Aggregate for each ward
            ward_metrics = {}
            for ward_id in ward_ids:
                ward_metrics[ward_id] = self.aggregate_complaints(ward_id, hours)
            
            logger.info("all_wards_aggregated", ward_count=len(ward_metrics))
            
            return ward_metrics
        
        except Exception as exc:
            logger.error("all_wards_aggregation_failed", error=str(exc))
            return {}

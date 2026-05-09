"""Ward infrastructure metrics aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.analytics_aggregator.schemas import WardMetrics
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class WardAggregator:
    """Aggregate ward infrastructure metrics."""

    def __init__(self):
        """Initialize ward aggregator."""
        self.db = db

    def aggregate_ward(self, ward_id: str, days: int = 30) -> WardMetrics:
        """
        Aggregate ward infrastructure metrics.
        
        Args:
            ward_id: Ward identifier
            days: Number of days to look back
        
        Returns:
            WardMetrics with aggregated infrastructure scores
        """
        try:
            # Calculate time window
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # Query ward reports
            ward_reports = []
            
            try:
                query = (
                    self.db.collection("ward_reports")
                    .where("wardId", "==", ward_id)
                )
                
                for doc in query.stream():
                    report_data = doc.to_dict()
                    created_at = report_data.get("createdAt")
                    
                    if created_at and created_at >= cutoff_time:
                        ward_reports.append(report_data)
            except Exception:
                # Collection might not exist
                pass
            
            # Calculate average scores
            if ward_reports:
                road_scores = [r.get("roadQualityScore", 50.0) for r in ward_reports]
                sanitation_scores = [r.get("sanitationScore", 50.0) for r in ward_reports]
                flood_scores = [r.get("floodRiskScore", 50.0) for r in ward_reports]
                green_scores = [r.get("greenCoverageScore", 50.0) for r in ward_reports]
                
                road_quality = sum(road_scores) / len(road_scores)
                sanitation = sum(sanitation_scores) / len(sanitation_scores)
                flood_risk = sum(flood_scores) / len(flood_scores)
                green_coverage = sum(green_scores) / len(green_scores)
            else:
                # Default scores if no reports
                road_quality = 50.0
                sanitation = 50.0
                flood_risk = 50.0
                green_coverage = 50.0
            
            # Calculate overall infrastructure score
            overall = (road_quality + sanitation + (100 - flood_risk) + green_coverage) / 4
            
            logger.info(
                "ward_aggregated",
                ward_id=ward_id,
                overall_score=overall,
                reports=len(ward_reports),
            )
            
            return WardMetrics(
                wardId=ward_id,
                roadQualityScore=round(road_quality, 2),
                sanitationScore=round(sanitation, 2),
                floodRiskScore=round(flood_risk, 2),
                greenCoverageScore=round(green_coverage, 2),
                overallInfrastructureScore=round(overall, 2),
            )
        
        except Exception as exc:
            logger.error("ward_aggregation_failed", ward_id=ward_id, error=str(exc))
            return WardMetrics(
                wardId=ward_id,
                roadQualityScore=50.0,
                sanitationScore=50.0,
                floodRiskScore=50.0,
                greenCoverageScore=50.0,
                overallInfrastructureScore=50.0,
            )

    def aggregate_all_wards(self, days: int = 30) -> list[WardMetrics]:
        """Aggregate infrastructure metrics for all wards."""
        try:
            # Get unique ward IDs
            ward_ids = set()
            
            try:
                for doc in self.db.collection("ward_reports").stream():
                    report_data = doc.to_dict()
                    ward_id = report_data.get("wardId")
                    if ward_id:
                        ward_ids.add(ward_id)
            except Exception:
                pass
            
            # Also check complaints for ward IDs
            try:
                for doc in self.db.collection("complaints").limit(1000).stream():
                    complaint_data = doc.to_dict()
                    ward_id = complaint_data.get("wardId")
                    if ward_id:
                        ward_ids.add(ward_id)
            except Exception:
                pass
            
            # Aggregate for each ward
            ward_metrics = []
            for ward_id in ward_ids:
                metrics = self.aggregate_ward(ward_id, days)
                ward_metrics.append(metrics)
            
            logger.info("all_wards_infrastructure_aggregated", ward_count=len(ward_metrics))
            
            return ward_metrics
        
        except Exception as exc:
            logger.error("all_wards_infrastructure_aggregation_failed", error=str(exc))
            return []

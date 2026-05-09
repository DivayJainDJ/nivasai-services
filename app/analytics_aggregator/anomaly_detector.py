"""Anomaly detection for municipal analytics."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.analytics_aggregator.schemas import AnomalyReport, ComplaintMetrics, WardMetrics
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class AnomalyDetector:
    """Detect anomalies in municipal data."""

    def __init__(self):
        """Initialize anomaly detector."""
        self.db = db
        self.thresholds = {
            "complaint_spike": 2.0,  # 2x standard deviation
            "escalation_surge": 2.5,
            "infrastructure_deterioration": 15.0,  # 15 point drop
            "flood_risk_surge": 20.0,  # 20 point increase
        }

    def detect_complaint_spike(
        self,
        current_metrics: ComplaintMetrics,
        ward_id: Optional[str] = None,
    ) -> Optional[AnomalyReport]:
        """Detect sudden complaint spikes."""
        try:
            # Get historical average
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            historical_counts = []
            query = self.db.collection("complaints")
            
            if ward_id:
                query = query.where("wardId", "==", ward_id)
            
            for doc in query.stream():
                complaint_data = doc.to_dict()
                created_at = complaint_data.get("createdAt")
                
                if created_at and created_at >= cutoff:
                    historical_counts.append(1)
            
            if not historical_counts:
                return None
            
            # Calculate daily average
            days = 30
            avg_daily = len(historical_counts) / days
            
            # Check if current is anomalous
            current_daily = current_metrics.totalComplaints
            
            if current_daily > avg_daily * self.thresholds["complaint_spike"]:
                deviation = ((current_daily - avg_daily) / avg_daily) * 100
                
                return AnomalyReport(
                    anomalyType="complaint_spike",
                    severity="high" if deviation > 100 else "medium",
                    wardId=ward_id,
                    description=f"Complaint volume {deviation:.1f}% above normal",
                    metricValue=current_daily,
                    expectedValue=avg_daily,
                    deviationPercent=round(deviation, 2),
                )
            
            return None
        
        except Exception as exc:
            logger.error("complaint_spike_detection_failed", error=str(exc))
            return None

    def detect_infrastructure_deterioration(
        self,
        current_metrics: WardMetrics,
    ) -> Optional[AnomalyReport]:
        """Detect infrastructure deterioration."""
        try:
            # Get historical metrics
            cutoff = datetime.utcnow() - timedelta(days=60)
            
            historical_scores = []
            
            try:
                query = (
                    self.db.collection("ward_reports")
                    .where("wardId", "==", current_metrics.wardId)
                )
                
                for doc in query.stream():
                    report_data = doc.to_dict()
                    created_at = report_data.get("createdAt")
                    
                    if created_at and created_at >= cutoff:
                        score = report_data.get("overallInfrastructureScore", 50.0)
                        historical_scores.append(score)
            except Exception:
                pass
            
            if not historical_scores:
                return None
            
            avg_historical = sum(historical_scores) / len(historical_scores)
            current_score = current_metrics.overallInfrastructureScore
            
            drop = avg_historical - current_score
            
            if drop > self.thresholds["infrastructure_deterioration"]:
                deviation = (drop / avg_historical) * 100
                
                return AnomalyReport(
                    anomalyType="infrastructure_deterioration",
                    severity="critical" if drop > 25 else "high",
                    wardId=current_metrics.wardId,
                    description=f"Infrastructure score dropped {drop:.1f} points",
                    metricValue=current_score,
                    expectedValue=avg_historical,
                    deviationPercent=round(deviation, 2),
                )
            
            return None
        
        except Exception as exc:
            logger.error("infrastructure_deterioration_detection_failed", error=str(exc))
            return None

    def detect_flood_risk_surge(
        self,
        current_metrics: WardMetrics,
    ) -> Optional[AnomalyReport]:
        """Detect flood risk surges."""
        try:
            # Check if flood risk is critically high
            if current_metrics.floodRiskScore > 70.0:
                return AnomalyReport(
                    anomalyType="flood_risk_surge",
                    severity="critical",
                    wardId=current_metrics.wardId,
                    description=f"Flood risk critically high at {current_metrics.floodRiskScore:.1f}",
                    metricValue=current_metrics.floodRiskScore,
                    expectedValue=50.0,
                    deviationPercent=round(
                        ((current_metrics.floodRiskScore - 50.0) / 50.0) * 100, 2
                    ),
                )
            
            return None
        
        except Exception as exc:
            logger.error("flood_risk_detection_failed", error=str(exc))
            return None

    def detect_all_anomalies(
        self,
        complaint_metrics: Optional[ComplaintMetrics] = None,
        ward_metrics: Optional[list[WardMetrics]] = None,
    ) -> list[AnomalyReport]:
        """Detect all types of anomalies."""
        anomalies = []
        
        # Detect complaint spikes
        if complaint_metrics:
            anomaly = self.detect_complaint_spike(complaint_metrics, complaint_metrics.wardId)
            if anomaly:
                anomalies.append(anomaly)
        
        # Detect infrastructure issues
        if ward_metrics:
            for metrics in ward_metrics:
                # Infrastructure deterioration
                anomaly = self.detect_infrastructure_deterioration(metrics)
                if anomaly:
                    anomalies.append(anomaly)
                
                # Flood risk
                anomaly = self.detect_flood_risk_surge(metrics)
                if anomaly:
                    anomalies.append(anomaly)
        
        logger.info("anomalies_detected", count=len(anomalies))
        
        return anomalies

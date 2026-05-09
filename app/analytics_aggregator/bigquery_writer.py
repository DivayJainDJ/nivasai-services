"""BigQuery writer for analytics data."""

from __future__ import annotations

import os
from typing import Any, Optional

from app.analytics_aggregator.schemas import (
    AnomalyReport,
    ComplaintMetrics,
    EscalationMetrics,
    WardMetrics,
)
from app.analytics_aggregator.validator import validate_bigquery_table_name
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class BigQueryWriter:
    """Write analytics data to BigQuery."""

    def __init__(self):
        """Initialize BigQuery writer."""
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self.dataset = os.getenv("BIGQUERY_DATASET", "nivasai_analytics")
        self.client = None
        
        # Initialize client if configured
        if self.project_id:
            try:
                from google.cloud import bigquery
                self.client = bigquery.Client(project=self.project_id)
                logger.info("bigquery_client_initialized", project=self.project_id)
            except Exception as exc:
                logger.warning("bigquery_client_init_failed", error=str(exc))

    def write_ward_metrics(self, metrics: WardMetrics) -> bool:
        """Write ward metrics to BigQuery."""
        if not self.client:
            logger.warning("bigquery_not_configured")
            return False
        
        try:
            table_id = f"{self.project_id}.{self.dataset}.ward_metrics"
            
            rows_to_insert = [{
                "wardId": metrics.wardId,
                "roadQualityScore": metrics.roadQualityScore,
                "sanitationScore": metrics.sanitationScore,
                "floodRiskScore": metrics.floodRiskScore,
                "greenCoverageScore": metrics.greenCoverageScore,
                "overallInfrastructureScore": metrics.overallInfrastructureScore,
                "generatedAt": metrics.generatedAt.isoformat(),
            }]
            
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            
            if errors:
                logger.error("bigquery_insert_failed", errors=errors)
                return False
            
            logger.info("ward_metrics_written", ward_id=metrics.wardId)
            return True
        
        except Exception as exc:
            logger.error("bigquery_write_error", error=str(exc))
            return False

    def write_complaint_metrics(self, metrics: ComplaintMetrics) -> bool:
        """Write complaint metrics to BigQuery."""
        if not self.client:
            return False
        
        try:
            table_id = f"{self.project_id}.{self.dataset}.complaint_metrics"
            
            rows_to_insert = [{
                "wardId": metrics.wardId,
                "totalComplaints": metrics.totalComplaints,
                "resolvedComplaints": metrics.resolvedComplaints,
                "pendingComplaints": metrics.pendingComplaints,
                "resolutionRate": metrics.resolutionRate,
                "averageResponseTimeHours": metrics.averageResponseTimeHours,
                "generatedAt": metrics.timestamp.isoformat(),
            }]
            
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            
            if not errors:
                logger.info("complaint_metrics_written", ward_id=metrics.wardId)
                return True
            
            return False
        
        except Exception as exc:
            logger.error("complaint_metrics_write_error", error=str(exc))
            return False

    def write_escalation_metrics(self, metrics: EscalationMetrics) -> bool:
        """Write escalation metrics to BigQuery."""
        if not self.client:
            return False
        
        try:
            table_id = f"{self.project_id}.{self.dataset}.escalation_metrics"
            
            rows_to_insert = [{
                "totalEscalations": metrics.totalEscalations,
                "slaBreaches": metrics.slaBreaches,
                "emergencyIncidents": metrics.emergencyIncidents,
                "criticalComplaintDensity": metrics.criticalComplaintDensity,
                "escalationRate": metrics.escalationRate,
                "generatedAt": metrics.timestamp.isoformat(),
            }]
            
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            
            if not errors:
                logger.info("escalation_metrics_written")
                return True
            
            return False
        
        except Exception as exc:
            logger.error("escalation_metrics_write_error", error=str(exc))
            return False

    def write_anomaly(self, anomaly: AnomalyReport) -> bool:
        """Write anomaly report to BigQuery."""
        if not self.client:
            return False
        
        try:
            table_id = f"{self.project_id}.{self.dataset}.anomaly_reports"
            
            rows_to_insert = [{
                "anomalyType": anomaly.anomalyType,
                "severity": anomaly.severity,
                "wardId": anomaly.wardId,
                "description": anomaly.description,
                "metricValue": anomaly.metricValue,
                "expectedValue": anomaly.expectedValue,
                "deviationPercent": anomaly.deviationPercent,
                "detectedAt": anomaly.detectedAt.isoformat(),
            }]
            
            errors = self.client.insert_rows_json(table_id, rows_to_insert)
            
            if not errors:
                logger.info("anomaly_written", type=anomaly.anomalyType)
                return True
            
            return False
        
        except Exception as exc:
            logger.error("anomaly_write_error", error=str(exc))
            return False

    def batch_write(self, rows: list[dict[str, Any]], table: str) -> bool:
        """Batch write rows to BigQuery."""
        if not self.client or not validate_bigquery_table_name(table):
            return False
        
        try:
            table_id = f"{self.project_id}.{self.dataset}.{table}"
            errors = self.client.insert_rows_json(table_id, rows)
            
            if not errors:
                logger.info("batch_write_completed", table=table, rows=len(rows))
                return True
            
            logger.error("batch_write_failed", errors=errors)
            return False
        
        except Exception as exc:
            logger.error("batch_write_error", error=str(exc))
            return False

"""Main analytics aggregation service."""

from __future__ import annotations

import time
import uuid
from datetime import datetime

from app.analytics_aggregator.anomaly_detector import AnomalyDetector
from app.analytics_aggregator.bigquery_writer import BigQueryWriter
from app.analytics_aggregator.brief_generator import BriefGenerator
from app.analytics_aggregator.complaint_aggregator import ComplaintAggregator
from app.analytics_aggregator.escalation_aggregator import EscalationAggregator
from app.analytics_aggregator.routing_aggregator import RoutingAggregator
from app.analytics_aggregator.schemas import AnalyticsJobResult
from app.analytics_aggregator.sql_generator import SQLGenerator
from app.analytics_aggregator.ward_aggregator import WardAggregator
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class AnalyticsAggregatorService:
    """Main analytics aggregation service."""

    def __init__(self):
        """Initialize analytics service."""
        self.complaint_aggregator = ComplaintAggregator()
        self.routing_aggregator = RoutingAggregator()
        self.escalation_aggregator = EscalationAggregator()
        self.ward_aggregator = WardAggregator()
        self.bigquery_writer = BigQueryWriter()
        self.sql_generator = SQLGenerator()
        self.anomaly_detector = AnomalyDetector()
        self.brief_generator = BriefGenerator()

    def run_analytics_job(self) -> AnalyticsJobResult:
        """
        Run complete analytics aggregation job.
        
        Returns:
            AnalyticsJobResult with all aggregated metrics
        """
        job_id = str(uuid.uuid4())
        start_time = time.time()
        errors = []
        
        logger.info("analytics_job_started", job_id=job_id)
        
        try:
            # 1. Aggregate complaint metrics
            logger.info("aggregating_complaints")
            complaint_metrics = self.complaint_aggregator.aggregate_complaints(hours=24)
            
            # 2. Aggregate routing metrics
            logger.info("aggregating_routing")
            routing_metrics = self.routing_aggregator.aggregate_routing(hours=24)
            
            # 3. Aggregate escalation metrics
            logger.info("aggregating_escalations")
            escalation_metrics = self.escalation_aggregator.aggregate_escalations(hours=24)
            
            # 4. Aggregate ward metrics
            logger.info("aggregating_wards")
            ward_metrics = self.ward_aggregator.aggregate_all_wards(days=30)
            
            # 5. Detect anomalies
            logger.info("detecting_anomalies")
            anomalies = self.anomaly_detector.detect_all_anomalies(
                complaint_metrics=complaint_metrics,
                ward_metrics=ward_metrics,
            )
            
            # 6. Generate ward briefs
            logger.info("generating_ward_briefs")
            ward_briefs = []
            
            # Generate briefs for wards with metrics
            ward_complaint_metrics = self.complaint_aggregator.aggregate_all_wards(hours=24)
            
            for ward_metric in ward_metrics[:10]:  # Limit to top 10 wards
                ward_id = ward_metric.wardId
                ward_complaints = ward_complaint_metrics.get(ward_id)
                
                if ward_complaints:
                    brief = self.brief_generator.generate_ward_brief(
                        ward_id,
                        ward_metric,
                        ward_complaints,
                    )
                    ward_briefs.append(brief)
            
            # 7. Write to BigQuery
            logger.info("writing_to_bigquery")
            
            # Write complaint metrics
            if complaint_metrics.totalComplaints > 0:
                self.bigquery_writer.write_complaint_metrics(complaint_metrics)
            
            # Write escalation metrics
            if escalation_metrics.totalEscalations > 0:
                self.bigquery_writer.write_escalation_metrics(escalation_metrics)
            
            # Write ward metrics
            for ward_metric in ward_metrics:
                self.bigquery_writer.write_ward_metrics(ward_metric)
            
            # Write anomalies
            for anomaly in anomalies:
                self.bigquery_writer.write_anomaly(anomaly)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            logger.info(
                "analytics_job_completed",
                job_id=job_id,
                execution_time=execution_time,
                wards=len(ward_metrics),
                anomalies=len(anomalies),
            )
            
            return AnalyticsJobResult(
                jobId=job_id,
                status="success",
                complaintMetrics=complaint_metrics,
                routingMetrics=routing_metrics,
                escalationMetrics=escalation_metrics,
                wardMetrics=ward_metrics,
                anomalies=anomalies,
                wardBriefs=ward_briefs,
                executionTimeSeconds=round(execution_time, 2),
                errors=errors,
            )
        
        except Exception as exc:
            logger.error("analytics_job_failed", job_id=job_id, error=str(exc))
            errors.append(str(exc))
            
            return AnalyticsJobResult(
                jobId=job_id,
                status="failed",
                executionTimeSeconds=time.time() - start_time,
                errors=errors,
            )

    def get_ward_summary(self, ward_id: str) -> dict:
        """Get summary for specific ward."""
        try:
            complaint_metrics = self.complaint_aggregator.aggregate_complaints(ward_id, hours=24)
            ward_metrics = self.ward_aggregator.aggregate_ward(ward_id, days=30)
            
            brief = self.brief_generator.generate_ward_brief(
                ward_id,
                ward_metrics,
                complaint_metrics,
            )
            
            return {
                "wardId": ward_id,
                "complaints": complaint_metrics.model_dump(),
                "infrastructure": ward_metrics.model_dump(),
                "brief": brief.model_dump(),
            }
        
        except Exception as exc:
            logger.error("ward_summary_failed", ward_id=ward_id, error=str(exc))
            return {"error": str(exc)}

"""SQL query generation for BigQuery analytics."""

from __future__ import annotations

from typing import Optional

from app.analytics_aggregator.validator import sanitize_sql_identifier, validate_sql_safety
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class SQLGenerator:
    """Generate BigQuery SQL queries."""

    def __init__(self, dataset: str = "nivasai_analytics"):
        """Initialize SQL generator."""
        self.dataset = dataset

    def generate_ward_metrics_insert(self, ward_id: str) -> str:
        """Generate SQL to insert ward metrics."""
        ward_id_safe = sanitize_sql_identifier(ward_id)
        
        sql = f"""
        INSERT INTO `{self.dataset}.ward_metrics`
        (wardId, roadQualityScore, sanitationScore, floodRiskScore, 
         greenCoverageScore, overallInfrastructureScore, generatedAt)
        VALUES
        (@wardId, @roadQualityScore, @sanitationScore, @floodRiskScore,
         @greenCoverageScore, @overallInfrastructureScore, CURRENT_TIMESTAMP())
        """
        
        return sql.strip()

    def generate_complaint_metrics_insert(self) -> str:
        """Generate SQL to insert complaint metrics."""
        sql = f"""
        INSERT INTO `{self.dataset}.complaint_metrics`
        (wardId, totalComplaints, resolvedComplaints, pendingComplaints,
         resolutionRate, averageResponseTimeHours, generatedAt)
        VALUES
        (@wardId, @totalComplaints, @resolvedComplaints, @pendingComplaints,
         @resolutionRate, @averageResponseTimeHours, CURRENT_TIMESTAMP())
        """
        
        return sql.strip()

    def generate_escalation_metrics_insert(self) -> str:
        """Generate SQL to insert escalation metrics."""
        sql = f"""
        INSERT INTO `{self.dataset}.escalation_metrics`
        (totalEscalations, slaBreaches, emergencyIncidents,
         criticalComplaintDensity, escalationRate, generatedAt)
        VALUES
        (@totalEscalations, @slaBreaches, @emergencyIncidents,
         @criticalComplaintDensity, @escalationRate, CURRENT_TIMESTAMP())
        """
        
        return sql.strip()

    def generate_anomaly_insert(self) -> str:
        """Generate SQL to insert anomaly report."""
        sql = f"""
        INSERT INTO `{self.dataset}.anomaly_reports`
        (anomalyType, severity, wardId, description, metricValue,
         expectedValue, deviationPercent, detectedAt)
        VALUES
        (@anomalyType, @severity, @wardId, @description, @metricValue,
         @expectedValue, @deviationPercent, CURRENT_TIMESTAMP())
        """
        
        return sql.strip()

    def generate_trend_analysis(self, ward_id: Optional[str] = None, days: int = 30) -> str:
        """Generate SQL for trend analysis."""
        where_clause = f"WHERE wardId = '{sanitize_sql_identifier(ward_id)}'" if ward_id else ""
        
        sql = f"""
        SELECT
            wardId,
            DATE(generatedAt) as date,
            AVG(roadQualityScore) as avg_road_quality,
            AVG(sanitationScore) as avg_sanitation,
            AVG(floodRiskScore) as avg_flood_risk,
            AVG(overallInfrastructureScore) as avg_overall
        FROM `{self.dataset}.ward_metrics`
        {where_clause}
        WHERE generatedAt >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY wardId, date
        ORDER BY date DESC
        """
        
        if not validate_sql_safety(sql):
            raise ValueError("Generated SQL failed safety validation")
        
        return sql.strip()

    def generate_complaint_trend(self, ward_id: Optional[str] = None, days: int = 30) -> str:
        """Generate SQL for complaint trend analysis."""
        where_clause = f"WHERE wardId = '{sanitize_sql_identifier(ward_id)}'" if ward_id else ""
        
        sql = f"""
        SELECT
            wardId,
            DATE(generatedAt) as date,
            SUM(totalComplaints) as daily_complaints,
            AVG(resolutionRate) as avg_resolution_rate,
            AVG(averageResponseTimeHours) as avg_response_time
        FROM `{self.dataset}.complaint_metrics`
        {where_clause}
        WHERE generatedAt >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY wardId, date
        ORDER BY date DESC
        """
        
        if not validate_sql_safety(sql):
            raise ValueError("Generated SQL failed safety validation")
        
        return sql.strip()

    def generate_rolling_average(
        self,
        table: str,
        metric: str,
        window_days: int = 7,
    ) -> str:
        """Generate SQL for rolling average calculation."""
        table_safe = sanitize_sql_identifier(table)
        metric_safe = sanitize_sql_identifier(metric)
        
        sql = f"""
        SELECT
            wardId,
            generatedAt,
            {metric_safe},
            AVG({metric_safe}) OVER (
                PARTITION BY wardId
                ORDER BY generatedAt
                ROWS BETWEEN {window_days} PRECEDING AND CURRENT ROW
            ) as rolling_avg_{metric_safe}
        FROM `{self.dataset}.{table_safe}`
        WHERE generatedAt >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        ORDER BY wardId, generatedAt DESC
        """
        
        if not validate_sql_safety(sql):
            raise ValueError("Generated SQL failed safety validation")
        
        return sql.strip()

    def generate_anomaly_detection_query(
        self,
        table: str,
        metric: str,
        threshold_stddev: float = 2.0,
    ) -> str:
        """Generate SQL for anomaly detection."""
        table_safe = sanitize_sql_identifier(table)
        metric_safe = sanitize_sql_identifier(metric)
        
        sql = f"""
        WITH stats AS (
            SELECT
                wardId,
                AVG({metric_safe}) as mean_value,
                STDDEV({metric_safe}) as stddev_value
            FROM `{self.dataset}.{table_safe}`
            WHERE generatedAt >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            GROUP BY wardId
        ),
        recent AS (
            SELECT
                wardId,
                {metric_safe} as current_value,
                generatedAt
            FROM `{self.dataset}.{table_safe}`
            WHERE generatedAt >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
        )
        SELECT
            r.wardId,
            r.current_value,
            s.mean_value,
            s.stddev_value,
            ABS(r.current_value - s.mean_value) / s.stddev_value as z_score
        FROM recent r
        JOIN stats s ON r.wardId = s.wardId
        WHERE ABS(r.current_value - s.mean_value) / s.stddev_value > {threshold_stddev}
        ORDER BY z_score DESC
        """
        
        if not validate_sql_safety(sql):
            raise ValueError("Generated SQL failed safety validation")
        
        return sql.strip()

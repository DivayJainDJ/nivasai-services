"""
Pydantic schemas for monitoring and analytics data structures
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ServiceHealth(str, Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class Metric(BaseModel):
    """System metric"""
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit")
    metric_type: MetricType = Field(..., description="Metric type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metric timestamp")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metric labels")
    
    class Config:
        from_attributes = True


class ServiceMetrics(BaseModel):
    """Service-specific metrics"""
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    request_count: int = Field(..., description="Total request count")
    error_count: int = Field(..., description="Total error count")
    avg_response_time: float = Field(..., description="Average response time in ms")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")
    active_connections: int = Field(..., description="Active connections")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class HealthCheck(BaseModel):
    """Health check result"""
    service_name: str = Field(..., description="Service name")
    status: ServiceHealth = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    response_time_ms: float = Field(..., description="Response time in ms")
    details: Dict[str, Any] = Field(default_factory=dict, description="Health check details")
    dependencies: Dict[str, ServiceHealth] = Field(default_factory=dict, description="Dependency health")
    
    class Config:
        from_attributes = True


class Alert(BaseModel):
    """System alert"""
    alert_id: str = Field(..., description="Alert ID")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    severity: AlertSeverity = Field(..., description="Alert severity")
    service: str = Field(..., description="Affected service")
    metric_name: str = Field(..., description="Related metric")
    threshold: float = Field(..., description="Alert threshold")
    current_value: float = Field(..., description="Current metric value")
    triggered_at: datetime = Field(default_factory=datetime.utcnow, description="Alert trigger time")
    resolved_at: Optional[datetime] = Field(None, description="Alert resolution time")
    status: str = Field(default="active", description="Alert status")
    labels: Dict[str, str] = Field(default_factory=dict, description="Alert labels")
    
    class Config:
        from_attributes = True


class AnalyticsReport(BaseModel):
    """Analytics report"""
    report_date: datetime = Field(..., description="Report date")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")
    complaint_analytics: Dict[str, Any] = Field(..., description="Complaint analytics")
    housing_analytics: Dict[str, Any] = Field(..., description="Housing analytics")
    whatsapp_analytics: Dict[str, Any] = Field(..., description="WhatsApp analytics")
    ward_analytics: Dict[str, Any] = Field(..., description="Ward analytics")
    trend_analysis: Dict[str, Any] = Field(..., description="Trend analysis")
    insights: List[str] = Field(..., description="AI-generated insights")
    kpis: Dict[str, Any] = Field(..., description="Key performance indicators")
    processing_time_seconds: float = Field(..., description="Processing time")
    
    class Config:
        from_attributes = True


class TrendAnalysis(BaseModel):
    """Trend analysis results"""
    complaint_trend: Dict[str, Any] = Field(..., description="Complaint trend data")
    housing_trend: Dict[str, Any] = Field(..., description="Housing trend data")
    whatsapp_trend: Dict[str, Any] = Field(..., description="WhatsApp trend data")
    patterns: List[str] = Field(..., description="Identified patterns")
    analysis_period: str = Field(..., description="Analysis period")
    comparison_period: str = Field(..., description="Comparison period")
    
    class Config:
        from_attributes = True


class WardMetrics(BaseModel):
    """Ward-specific metrics"""
    ward_id: str = Field(..., description="Ward ID")
    ward_name: str = Field(..., description="Ward name")
    complaint_count: int = Field(..., description="Number of complaints")
    infrastructure_score: float = Field(..., description="Infrastructure score")
    priority_level: str = Field(..., description="Priority level")
    last_analyzed: datetime = Field(..., description="Last analysis date")
    
    class Config:
        from_attributes = True


class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    service_efficiency: Dict[str, float] = Field(..., description="Service efficiency metrics")
    citizen_engagement: Dict[str, float] = Field(..., description="Citizen engagement metrics")
    housing_performance: Dict[str, float] = Field(..., description="Housing performance metrics")
    system_health: Dict[str, float] = Field(..., description="System health metrics")
    
    class Config:
        from_attributes = True


class DashboardData(BaseModel):
    """Dashboard data aggregation"""
    real_time_metrics: Dict[str, Any] = Field(..., description="Real-time metrics")
    last_24h_summary: Dict[str, Any] = Field(..., description="Last 24 hours summary")
    weekly_trends: Dict[str, Any] = Field(..., description="Weekly trends")
    active_alerts: List[Alert] = Field(..., description="Active alerts")
    service_health: Dict[str, HealthCheck] = Field(..., description="Service health status")
    top_wards: List[WardMetrics] = Field(..., description="Top performing wards")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Data timestamp")
    
    class Config:
        from_attributes = True


class SystemStatus(BaseModel):
    """Overall system status"""
    overall_health: ServiceHealth = Field(..., description="Overall system health")
    healthy_services: int = Field(..., description="Number of healthy services")
    degraded_services: int = Field(..., description="Number of degraded services")
    unhealthy_services: int = Field(..., description="Number of unhealthy services")
    active_alerts: int = Field(..., description="Number of active alerts")
    critical_alerts: int = Field(..., description="Number of critical alerts")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    class Config:
        from_attributes = True


class LogEntry(BaseModel):
    """Log entry for monitoring"""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Log timestamp")
    level: str = Field(..., description="Log level")
    service: str = Field(..., description="Service name")
    message: str = Field(..., description="Log message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Log context")
    request_id: Optional[str] = Field(None, description="Request ID")
    user_id: Optional[str] = Field(None, description="User ID")
    
    class Config:
        from_attributes = True


class ErrorMetrics(BaseModel):
    """Error metrics"""
    total_errors: int = Field(..., description="Total error count")
    error_rate: float = Field(..., description="Error rate percentage")
    errors_by_service: Dict[str, int] = Field(..., description="Errors by service")
    errors_by_type: Dict[str, int] = Field(..., description="Errors by type")
    recent_errors: List[LogEntry] = Field(..., description="Recent errors")
    
    class Config:
        from_attributes = True


class UsageMetrics(BaseModel):
    """Usage metrics"""
    active_users: int = Field(..., description="Active users count")
    total_requests: int = Field(..., description="Total requests")
    requests_per_minute: float = Field(..., description="Requests per minute")
    peak_concurrent_users: int = Field(..., description="Peak concurrent users")
    average_session_duration: float = Field(..., description="Average session duration")
    
    class Config:
        from_attributes = True


class ResourceMetrics(BaseModel):
    """Resource utilization metrics"""
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    disk_usage_gb: float = Field(..., description="Disk usage in GB")
    network_in_mb: float = Field(..., description="Network inbound in MB")
    network_out_mb: float = Field(..., description="Network outbound in MB")
    database_connections: int = Field(..., description="Database connections")
    
    class Config:
        from_attributes = True


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    alert_thresholds: Dict[str, float] = Field(..., description="Alert thresholds")
    health_check_intervals: Dict[str, int] = Field(..., description="Health check intervals in seconds")
    retention_days: int = Field(default=30, description="Data retention days")
    notification_channels: List[str] = Field(..., description="Notification channels")
    enabled_services: List[str] = Field(..., description="Enabled services for monitoring")
    
    class Config:
        from_attributes = True


class SLAReport(BaseModel):
    """Service Level Agreement report"""
    service_name: str = Field(..., description="Service name")
    period_start: datetime = Field(..., description="Reporting period start")
    period_end: datetime = Field(..., description="Reporting period end")
    uptime_percentage: float = Field(..., description="Uptime percentage")
    avg_response_time: float = Field(..., description="Average response time")
    error_rate: float = Field(..., description="Error rate percentage")
    sla_met: bool = Field(..., description="SLA compliance status")
    violations: List[Dict[str, Any]] = Field(..., description="SLA violations")
    
    class Config:
        from_attributes = True

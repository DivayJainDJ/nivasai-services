"""Analytics dashboard API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.analytics_aggregator.scheduler import get_scheduler
from app.analytics_aggregator.service import AnalyticsAggregatorService
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/analytics/ward/{ward_id}")
async def get_ward_analytics(ward_id: str) -> dict:
    """
    Get analytics for specific ward.
    
    Args:
        ward_id: Ward identifier
    
    Returns:
        Ward analytics including complaints, infrastructure, and AI brief
    """
    try:
        service = AnalyticsAggregatorService()
        summary = service.get_ward_summary(ward_id)
        
        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
        
        return summary
    
    except Exception as exc:
        logger.error("ward_analytics_failed", ward_id=ward_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/summary")
async def get_analytics_summary() -> dict:
    """
    Get overall analytics summary.
    
    Returns:
        Summary of all analytics metrics
    """
    try:
        service = AnalyticsAggregatorService()
        
        # Run aggregation
        result = service.run_analytics_job()
        
        # Build summary
        summary = {
            "jobId": result.jobId,
            "status": result.status,
            "timestamp": result.timestamp.isoformat(),
            "executionTimeSeconds": result.executionTimeSeconds,
            "metrics": {
                "totalComplaints": result.complaintMetrics.totalComplaints if result.complaintMetrics else 0,
                "totalWards": len(result.wardMetrics),
                "anomaliesDetected": len(result.anomalies),
                "wardsAnalyzed": len(result.wardBriefs),
            },
            "complaints": result.complaintMetrics.model_dump() if result.complaintMetrics else None,
            "routing": result.routingMetrics.model_dump() if result.routingMetrics else None,
            "escalations": result.escalationMetrics.model_dump() if result.escalationMetrics else None,
        }
        
        return summary
    
    except Exception as exc:
        logger.error("analytics_summary_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/anomalies")
async def get_anomalies() -> dict:
    """
    Get detected anomalies.
    
    Returns:
        List of detected anomalies
    """
    try:
        service = AnalyticsAggregatorService()
        
        # Run aggregation to get latest anomalies
        result = service.run_analytics_job()
        
        return {
            "anomalies": [anomaly.model_dump() for anomaly in result.anomalies],
            "count": len(result.anomalies),
            "timestamp": result.timestamp.isoformat(),
        }
    
    except Exception as exc:
        logger.error("anomalies_fetch_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/analytics/scheduler/status")
async def get_scheduler_status() -> dict:
    """
    Get analytics scheduler status.
    
    Returns:
        Scheduler status and next run time
    """
    try:
        scheduler = get_scheduler()
        
        if not scheduler:
            return {
                "status": "not_initialized",
                "message": "Analytics scheduler not initialized",
            }
        
        return scheduler.get_status()
    
    except Exception as exc:
        logger.error("scheduler_status_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/analytics/run-now")
async def trigger_analytics_now() -> dict:
    """
    Manually trigger analytics aggregation.
    
    Returns:
        Job execution result
    """
    try:
        service = AnalyticsAggregatorService()
        result = service.run_analytics_job()
        
        return {
            "jobId": result.jobId,
            "status": result.status,
            "executionTimeSeconds": result.executionTimeSeconds,
            "metrics": {
                "wards": len(result.wardMetrics),
                "anomalies": len(result.anomalies),
                "briefs": len(result.wardBriefs),
            },
        }
    
    except Exception as exc:
        logger.error("manual_analytics_trigger_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

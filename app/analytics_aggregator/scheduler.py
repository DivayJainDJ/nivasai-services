"""Scheduler for hourly analytics aggregation."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.analytics_aggregator.service import AnalyticsAggregatorService
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class AnalyticsScheduler:
    """Schedule hourly analytics aggregation jobs."""

    def __init__(self):
        """Initialize analytics scheduler."""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.service = AnalyticsAggregatorService()
        self.is_running = False

    def start(self) -> None:
        """Start the analytics scheduler."""
        if self.is_running:
            logger.warning("scheduler_already_running")
            return
        
        try:
            self.scheduler = AsyncIOScheduler()
            
            # Schedule hourly job (at minute 0 of every hour)
            self.scheduler.add_job(
                self._run_analytics_job,
                trigger=CronTrigger(minute=0),  # Run at the top of every hour
                id="analytics_aggregation",
                name="Hourly Analytics Aggregation",
                replace_existing=True,
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("analytics_scheduler_started", next_run=self._get_next_run_time())
        
        except Exception as exc:
            logger.error("scheduler_start_failed", error=str(exc))

    def stop(self) -> None:
        """Stop the analytics scheduler."""
        if not self.is_running or not self.scheduler:
            return
        
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("analytics_scheduler_stopped")
        
        except Exception as exc:
            logger.error("scheduler_stop_failed", error=str(exc))

    async def _run_analytics_job(self) -> None:
        """Run analytics aggregation job."""
        try:
            logger.info("scheduled_analytics_job_triggered")
            
            # Run analytics job
            result = self.service.run_analytics_job()
            
            logger.info(
                "scheduled_analytics_job_completed",
                job_id=result.jobId,
                status=result.status,
                execution_time=result.executionTimeSeconds,
            )
        
        except Exception as exc:
            logger.error("scheduled_analytics_job_failed", error=str(exc))

    def run_now(self) -> None:
        """Manually trigger analytics job immediately."""
        try:
            logger.info("manual_analytics_job_triggered")
            result = self.service.run_analytics_job()
            logger.info("manual_analytics_job_completed", job_id=result.jobId)
        
        except Exception as exc:
            logger.error("manual_analytics_job_failed", error=str(exc))

    def _get_next_run_time(self) -> Optional[str]:
        """Get next scheduled run time."""
        if not self.scheduler:
            return None
        
        job = self.scheduler.get_job("analytics_aggregation")
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        
        return None

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "is_running": self.is_running,
            "next_run_time": self._get_next_run_time(),
            "scheduler_state": "running" if self.is_running else "stopped",
        }


# Global scheduler instance
_scheduler_instance: Optional[AnalyticsScheduler] = None


def start_analytics_scheduler() -> None:
    """Start the global analytics scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = AnalyticsScheduler()
    
    _scheduler_instance.start()


def stop_analytics_scheduler() -> None:
    """Stop the global analytics scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance:
        _scheduler_instance.stop()


def get_scheduler() -> Optional[AnalyticsScheduler]:
    """Get the global scheduler instance."""
    return _scheduler_instance

"""
Time utilities for scheduling and timestamping.
"""

from datetime import datetime, timedelta
from typing import Optional


def get_current_timestamp() -> str:
    """Get current ISO 8601 timestamp."""
    return datetime.utcnow().isoformat() + "Z"


def is_sla_breached(
    created_at: str, sla_hours: int, current_time: Optional[str] = None
) -> bool:
    """
    Check if SLA time has been exceeded.

    Args:
        created_at: ISO 8601 timestamp when issue was created
        sla_hours: SLA time in hours
        current_time: Current time (defaults to now)

    Returns:
        True if SLA is breached
    """
    if current_time is None:
        current_time = get_current_timestamp()

    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    current = datetime.fromisoformat(current_time.replace("Z", "+00:00"))
    elapsed = current - created

    return elapsed > timedelta(hours=sla_hours)


def get_days_since(timestamp: str) -> int:
    """Get number of days since timestamp."""
    created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    now = datetime.utcnow().replace(tzinfo=created.tzinfo)
    return (now - created).days

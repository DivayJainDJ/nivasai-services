"""Validation utilities for analytics aggregator."""

from __future__ import annotations

import re
from typing import Any


class ValidationException(Exception):
    """Raised when validation fails."""


def validate_metric_range(value: float, min_val: float = 0.0, max_val: float = 100.0) -> bool:
    """Validate metric is within range."""
    return min_val <= value <= max_val


def validate_sql_safety(sql: str) -> bool:
    """Validate SQL query for safety."""
    # Check for dangerous operations
    dangerous_keywords = [
        "DROP",
        "DELETE",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "GRANT",
        "REVOKE",
    ]
    
    sql_upper = sql.upper()
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False
    
    return True


def validate_ward_id(ward_id: str) -> bool:
    """Validate ward ID format."""
    # Ward IDs should be alphanumeric
    return bool(re.match(r"^[A-Za-z0-9_-]+$", ward_id))


def validate_bigquery_table_name(table_name: str) -> bool:
    """Validate BigQuery table name."""
    # Table names should be alphanumeric with underscores
    return bool(re.match(r"^[a-z][a-z0-9_]*$", table_name))


def validate_aggregation_consistency(metrics: dict[str, Any]) -> bool:
    """Validate aggregation consistency."""
    # Check that totals match sums
    if "totalComplaints" in metrics and "complaintsByCategory" in metrics:
        total = metrics["totalComplaints"]
        category_sum = sum(metrics["complaintsByCategory"].values())
        
        # Allow small rounding differences
        if abs(total - category_sum) > 1:
            return False
    
    return True


def sanitize_sql_identifier(identifier: str) -> str:
    """Sanitize SQL identifier."""
    # Remove non-alphanumeric characters except underscore
    return re.sub(r"[^a-zA-Z0-9_]", "", identifier)


def validate_percentage(value: float) -> bool:
    """Validate percentage value."""
    return 0.0 <= value <= 100.0


def validate_timestamp(timestamp: Any) -> bool:
    """Validate timestamp format."""
    from datetime import datetime
    
    if isinstance(timestamp, datetime):
        return True
    
    if isinstance(timestamp, str):
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return True
        except:
            return False
    
    return False

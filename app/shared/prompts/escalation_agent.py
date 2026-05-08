"""
Escalation agent prompt template.
"""

ESCALATION_PROMPT = """Determine if this complaint should be escalated based on SLA and severity.

Complaint Details:
- Complaint ID: {complaint_id}
- Created At: {created_at}
- Current Time: {current_time}
- Severity: {severity}
- Category: {category}
- Status: {status}
- SLA Hours: {sla_hours}

Return JSON:
{{
    "should_escalate": <true|false>,
    "escalation_reason": "reason if escalating",
    "recommended_action": "action to take"
}}

Return ONLY valid JSON.
"""


def get_escalation_prompt(
    complaint_id: str, created_at: str, current_time: str, severity: str,
    category: str, status: str, sla_hours: int
) -> str:
    """Generate escalation prompt."""
    return ESCALATION_PROMPT.format(
        complaint_id=complaint_id,
        created_at=created_at,
        current_time=current_time,
        severity=severity,
        category=category,
        status=status,
        sla_hours=sla_hours,
    )

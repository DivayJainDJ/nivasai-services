"""Final response builder for ward analysis."""

from __future__ import annotations

from datetime import datetime, timezone


def build_ward_report(
    *,
    ward_name: str,
    city: str,
    state: str,
    population: int,
    scores_payload,
    remediation_payload,
) -> dict:
    return {
        "success": True,
        "ward": {
            "name": ward_name,
            "city": city,
            "state": state,
            "population": population,
        },
        "infrastructureScores": scores_payload.model_dump(),
        "remediationPlan": remediation_payload.model_dump(),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }

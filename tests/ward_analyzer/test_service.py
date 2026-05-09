from __future__ import annotations

from app.ward_analyzer import service
from app.ward_analyzer.validator import RemediationPayload, VisionScorePayload


def test_analyze_ward_success(monkeypatch):
    vision = VisionScorePayload(
        roadQuality=55,
        drainageQuality=42,
        sanitationQuality=61,
        greenCoverage=30,
        housingDensity=78,
        floodRisk=69,
        summary="Dense ward with drainage and flood vulnerabilities",
        confidence=0.86,
    )
    remediation = RemediationPayload(
        priorityLevel="high",
        keyProblems=["flood risk", "drainage weakness"],
        recommendedProjects=["Drain reconstruction", "Road resurfacing", "Stormwater channels"],
        estimatedBudgetINR=98000000,
        executionTimeline="18 months",
        riskAssessment="Monsoon disruption risk if delayed",
        phasedPlan=["Phase 1: emergency desilting", "Phase 2: drainage reconstruction", "Phase 3: road rehabilitation"],
        summary="Prioritize flood mitigation and drainage upgrades before road restoration.",
    )

    monkeypatch.setattr(service, "validate_satellite_image", lambda image_bytes, content_type: (image_bytes, content_type))
    monkeypatch.setattr(service, "score_infrastructure_from_satellite", lambda image_bytes, mime_type: vision)
    monkeypatch.setattr(
        service,
        "generate_remediation_plan",
        lambda ward_name, city, state, population, scores_payload: remediation,
    )

    report = service.analyze_ward(
        satellite_image_bytes=b"dummy",
        satellite_content_type="image/png",
        ward_name="Ward 12",
        population=152000,
        city="Bengaluru",
        state="Karnataka",
    )
    assert report["success"] is True
    assert report["ward"]["name"] == "Ward 12"
    assert report["infrastructureScores"]["floodRisk"] == 69
    assert report["remediationPlan"]["estimatedBudgetINR"] == 98000000


def test_analyze_ward_low_confidence_output(monkeypatch):
    vision = VisionScorePayload(
        roadQuality=40,
        drainageQuality=35,
        sanitationQuality=45,
        greenCoverage=22,
        housingDensity=81,
        floodRisk=72,
        summary="Image quality limited but suggests drainage stress",
        confidence=0.44,
    )
    remediation = RemediationPayload(
        priorityLevel="medium",
        keyProblems=["low confidence", "drainage stress"],
        recommendedProjects=["Field survey", "Drain cleaning"],
        estimatedBudgetINR=15000000,
        executionTimeline="6 months",
        riskAssessment="Requires on-ground verification before major capex",
        phasedPlan=["Phase 1: verification", "Phase 2: targeted fixes"],
        summary="Use a verification-first approach due to low confidence.",
    )
    monkeypatch.setattr(service, "validate_satellite_image", lambda image_bytes, content_type: (image_bytes, content_type))
    monkeypatch.setattr(service, "score_infrastructure_from_satellite", lambda image_bytes, mime_type: vision)
    monkeypatch.setattr(
        service,
        "generate_remediation_plan",
        lambda ward_name, city, state, population, scores_payload: remediation,
    )

    report = service.analyze_ward(
        satellite_image_bytes=b"dummy",
        satellite_content_type="image/jpeg",
        ward_name="Ward 19",
        population=98000,
        city="Mysuru",
        state="Karnataka",
    )
    assert report["success"] is True
    assert report["infrastructureScores"]["confidence"] == 0.44
    assert report["remediationPlan"]["priorityLevel"] == "medium"

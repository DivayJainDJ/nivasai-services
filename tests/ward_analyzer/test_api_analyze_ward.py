from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


def test_analyze_ward_api_success(monkeypatch):
    from app.api import analyze_ward as api_module

    monkeypatch.setattr(
        api_module,
        "analyze_ward",
        lambda **kwargs: {
            "success": True,
            "ward": {
                "name": kwargs["ward_name"],
                "city": kwargs["city"],
                "state": kwargs["state"],
                "population": kwargs["population"],
            },
            "infrastructureScores": {
                "roadQuality": 58,
                "drainageQuality": 46,
                "sanitationQuality": 62,
                "greenCoverage": 28,
                "housingDensity": 74,
                "floodRisk": 67,
                "summary": "Moderate stress with flood-risk pockets",
                "confidence": 0.82,
            },
            "remediationPlan": {
                "priorityLevel": "high",
                "keyProblems": ["flood risk", "drainage issues"],
                "recommendedProjects": ["Drainage upgrade", "Road repairs"],
                "estimatedBudgetINR": 54000000,
                "executionTimeline": "12 months",
                "riskAssessment": "Monsoon risk if interventions delayed",
                "phasedPlan": ["Survey", "Execution", "Stabilization"],
                "summary": "Prioritize drainage with concurrent corridor repairs.",
            },
            "generatedAt": "2026-01-01T00:00:00Z",
        },
    )

    client = TestClient(app)
    response = client.post(
        "/api/analyze-ward",
        data={
            "wardName": "Ward 7",
            "population": "123000",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        files={"satelliteImage": ("sat.png", BytesIO(b"png-bytes"), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["ward"]["name"] == "Ward 7"
    assert body["infrastructureScores"]["floodRisk"] == 67


def test_analyze_ward_api_invalid_population():
    client = TestClient(app)
    response = client.post(
        "/api/analyze-ward",
        data={
            "wardName": "Ward 2",
            "population": "0",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        files={"satelliteImage": ("sat.png", BytesIO(b"png-bytes"), "image/png")},
    )
    assert response.status_code == 400

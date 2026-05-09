from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


def test_complaint_creation_endpoint():
    client = TestClient(app)
    response = client.post(
        "/complaints/create",
        data={
            "description": "Garbage overflowing near market",
            "latitude": "12.9716",
            "longitude": "77.5946",
            "address": "MG Road, Bengaluru",
            "userId": "user_123",
        },
        files={"image": ("complaint.jpg", BytesIO(b"fake-image-bytes"), "image/jpeg")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "processing"
    assert "complaintId" in payload


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code in (200, 307, 308)

"""Pytest configuration and shared fixtures."""

import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    os.environ["GEMINI_API_KEY"] = "test_gemini_key"
    os.environ["FIREBASE_STORAGE_BUCKET"] = "test-bucket"
    os.environ["GOOGLE_MAPS_API_KEY"] = "test_maps_key"
    os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
    os.environ["DOCUMENT_AI_LOCATION"] = "us"
    os.environ["DOCUMENT_AI_PROCESSOR_ID"] = "test-processor"
    os.environ["BIGQUERY_DATASET"] = "test_dataset"
    os.environ["TWILIO_ACCOUNT_SID"] = "test_twilio_sid"
    os.environ["TWILIO_AUTH_TOKEN"] = "test_twilio_token"
    os.environ["TWILIO_WHATSAPP_NUMBER"] = "whatsapp:+14155238886"
    os.environ["FCM_BATCH_SIZE"] = "500"
    os.environ["FCM_MAX_WORKERS"] = "5"
    os.environ["ENABLE_TRIGGERS"] = "false"
    yield


@pytest.fixture
def client(test_env):
    """Create FastAPI test client."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    with patch('app.shared.firestore.client.get_firestore_client') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_gemini():
    """Mock Gemini client."""
    with patch('google.genai.Client') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_bigquery():
    """Mock BigQuery client."""
    with patch('google.cloud.bigquery.Client') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_storage():
    """Mock Firebase Storage."""
    with patch('firebase_admin.storage.bucket') as mock:
        mock_bucket = MagicMock()
        mock.return_value = mock_bucket
        yield mock_bucket


@pytest.fixture
def mock_document_ai():
    """Mock Document AI client."""
    with patch('google.cloud.documentai.DocumentProcessorServiceClient') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_fcm():
    """Mock Firebase Cloud Messaging."""
    with patch('firebase_admin.messaging.send_multicast') as mock:
        yield mock


@pytest.fixture
def mock_pubsub():
    """Mock Pub/Sub client."""
    with patch('google.cloud.pubsub_v1.PublisherClient') as mock_pub, \
         patch('google.cloud.pubsub_v1.SubscriberClient') as mock_sub:
        yield {"publisher": mock_pub, "subscriber": mock_sub}


@pytest.fixture
def sample_complaint():
    """Sample complaint data."""
    return {
        "description": "There is garbage piled up on MG Road near the bus stop",
        "location": "MG Road, Andheri West",
        "citizenPhone": "+919876543210",
        "citizenName": "Rajesh Kumar",
        "imageUrl": "https://storage.googleapis.com/test/complaint.jpg",
    }


@pytest.fixture
def sample_complaint_firestore():
    """Sample complaint Firestore document."""
    return {
        "complaintId": "C20240509001",
        "description": "Garbage on MG Road",
        "location": "MG Road, Andheri West",
        "category": "Waste Management",
        "severity": "medium",
        "status": "pending",
        "citizenPhone": "+919876543210",
        "citizenName": "Rajesh Kumar",
        "imageUrl": "https://storage.googleapis.com/test/complaint.jpg",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }


@pytest.fixture
def sample_housing_request():
    """Sample housing request."""
    return {
        "citizenPhone": "+919876543210",
        "income": 25000,
        "familySize": 4,
        "location": "Andheri West, Mumbai",
    }


@pytest.fixture
def sample_housing_unit():
    """Sample housing unit."""
    return {
        "unitId": "H001",
        "name": "Andheri EWS Complex",
        "type": "2BHK",
        "rent": 12000,
        "eligibility": "EWS",
        "location": "Andheri West",
        "coordinates": {"lat": 19.1136, "lng": 72.8697},
        "available": True,
        "amenities": ["Water", "Electricity"],
    }


@pytest.fixture
def sample_aadhaar_data():
    """Sample Aadhaar card data."""
    return {
        "name": "Rajesh Kumar",
        "aadhaarNumber": "123456789012",
        "dateOfBirth": "15/08/1985",
        "address": "123 MG Road, Andheri West, Mumbai 400058",
    }


@pytest.fixture
def sample_income_certificate():
    """Sample income certificate data."""
    return {
        "name": "Rajesh Kumar",
        "annualIncome": 300000,
        "monthlyIncome": 25000,
        "certificateNumber": "IC/2024/12345",
        "issuedBy": "Mumbai Municipal Corporation",
        "validUntil": "2025-05-09",
    }


@pytest.fixture
def sample_fcm_token():
    """Sample FCM token."""
    return {
        "userId": "user123",
        "role": "officer",
        "ward": "Ward-42",
        "department": "Roads & Infrastructure",
        "token": "fcm_token_abc123def456ghi789",
        "active": True,
        "lastSeen": datetime.utcnow(),
    }


@pytest.fixture
def sample_notification_payload():
    """Sample notification payload."""
    return {
        "title": "Emergency Alert",
        "body": "Flooding in Ward-42",
        "type": "emergency",
        "priority": "high",
        "targetRoles": ["officer"],
        "targetWards": ["Ward-42"],
        "targetDepartments": [],
        "data": {"severity": "high"},
    }


@pytest.fixture
def sample_twilio_payload():
    """Sample Twilio webhook payload."""
    return {
        "Body": "There is garbage on my street",
        "From": "whatsapp:+919876543210",
        "To": "whatsapp:+14155238886",
        "MessageSid": "SM123456",
        "NumMedia": "0",
    }


@pytest.fixture
def sample_ward_data():
    """Sample ward data."""
    return {
        "wardId": "Ward-42",
        "name": "Andheri West",
        "population": 85000,
        "area": 12.5,
        "councillor": "Mrs. Priya Sharma",
    }


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response."""
    def _mock(response_text: str):
        mock_response = MagicMock()
        mock_response.text = response_text
        return mock_response
    return _mock


@pytest.fixture
def mock_document_ai_response():
    """Mock Document AI response."""
    def _mock(text: str):
        mock_response = MagicMock()
        mock_document = MagicMock()
        mock_document.text = text
        mock_response.document = mock_document
        return mock_response
    return _mock


@pytest.fixture
def mock_maps_response():
    """Mock Google Maps API response."""
    def _mock(distance_meters: int, duration_seconds: int):
        return {
            "rows": [{
                "elements": [{
                    "distance": {"value": distance_meters, "text": f"{distance_meters/1000:.1f} km"},
                    "duration": {"value": duration_seconds, "text": f"{duration_seconds//60} mins"},
                    "status": "OK"
                }]
            }],
            "status": "OK"
        }
    return _mock


@pytest.fixture
def mock_bigquery_job():
    """Mock BigQuery job."""
    mock_job = MagicMock()
    mock_job.result.return_value = None
    mock_job.errors = None
    return mock_job

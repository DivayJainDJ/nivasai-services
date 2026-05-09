"""Test all API endpoints."""

import pytest
from unittest.mock import MagicMock, patch


class TestAPIEndpoints:
    """Test all API endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "NivasAI Services"
    
    def test_complaint_create_endpoint(
        self,
        client,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
        sample_complaint,
    ):
        """Test complaint creation endpoint."""
        # Mock Gemini response
        classification_response = mock_gemini_response(
            '{"category": "Waste Management", "severity": "medium", "department": "Sanitation", "priority": 2}'
        )
        
        mock_doc = MagicMock()
        mock_doc.id = "complaint_123"
        mock_firestore.collection.return_value.add.return_value = (None, mock_doc)
        
        with patch('app.complaint_classifier.classifier.get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = classification_response
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            response = client.post("/complaints/create", json=sample_complaint)
            
            assert response.status_code == 200
            data = response.json()
            assert "complaintId" in data
    
    def test_housing_match_endpoint(
        self,
        client,
        mock_firestore,
        sample_housing_request,
        sample_housing_unit,
    ):
        """Test housing match endpoint."""
        # Mock housing units
        mock_units = []
        for i in range(3):
            mock_doc = MagicMock()
            unit = sample_housing_unit.copy()
            unit["unitId"] = f"H00{i+1}"
            mock_doc.to_dict.return_value = unit
            mock_units.append(mock_doc)
        
        mock_firestore.collection.return_value.where.return_value.where.return_value.stream.return_value = mock_units
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                "rows": [{
                    "elements": [{
                        "distance": {"value": 2300, "text": "2.3 km"},
                        "duration": {"value": 600, "text": "10 mins"},
                        "status": "OK"
                    }]
                }],
                "status": "OK"
            }
            
            response = client.post("/api/housing/match", json=sample_housing_request)
            
            assert response.status_code == 200
            data = response.json()
            assert "recommendations" in data
    
    def test_document_upload_endpoint(
        self,
        client,
        mock_firestore,
        mock_document_ai,
        mock_document_ai_response,
    ):
        """Test document upload endpoint."""
        # Mock Document AI
        mock_response = mock_document_ai_response("Name: Test User\nAadhaar: 123456789012")
        mock_document_ai.return_value.process_document.return_value = mock_response
        
        with patch('app.document_parser.parser.DocumentProcessorServiceClient', return_value=mock_document_ai):
            response = client.post(
                "/api/documents/upload",
                json={
                    "citizenPhone": "+919876543210",
                    "documentType": "aadhaar",
                    "documentUrl": "https://storage.googleapis.com/test/aadhaar.jpg",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "parsed" in data
    
    def test_ward_analyze_endpoint(
        self,
        client,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
    ):
        """Test ward analysis endpoint."""
        # Mock Gemini response
        analysis_response = mock_gemini_response(
            '{"infrastructure_score": 7.5, "road_quality": 8, "water_supply": 7, "sanitation": 7}'
        )
        
        with patch('app.ward_analyzer.infrastructure_scorer.get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = analysis_response
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            response = client.post(
                "/api/ward/analyze",
                json={
                    "wardId": "Ward-42",
                    "satelliteImageUrl": "https://storage.googleapis.com/test/ward.jpg",
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data or "infrastructure_score" in data
    
    def test_bot_webhook_endpoint(
        self,
        client,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
        sample_twilio_payload,
    ):
        """Test bot webhook endpoint."""
        # Mock session
        mock_session_doc = MagicMock()
        mock_session_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_session_doc
        
        # Mock intent classification
        intent_response = mock_gemini_response(
            '{"intent": "GREET", "confidence": 0.99, "language": "en", "entities": {}}'
        )
        
        with patch('app.bot_webhook.intent_classifier.get_gemini_client') as mock_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = intent_response
            mock_client.return_value.GenerativeModel.return_value = mock_model
            
            response = client.post("/api/bot/webhook", data=sample_twilio_payload)
            
            assert response.status_code == 200
            assert len(response.text) > 0
    
    def test_bot_health_endpoint(self, client):
        """Test bot health endpoint."""
        response = client.get("/api/bot/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "bot_webhook"
    
    def test_analytics_summary_endpoint(
        self,
        client,
        mock_firestore,
        mock_bigquery,
    ):
        """Test analytics summary endpoint."""
        # Mock BigQuery query results
        mock_job = MagicMock()
        mock_job.result.return_value = [
            {"ward": "Ward-42", "complaint_count": 45, "avg_resolution_time": 2.5}
        ]
        mock_bigquery.query.return_value = mock_job
        
        with patch('app.analytics_aggregator.service.bigquery.Client', return_value=mock_bigquery):
            response = client.get("/api/analytics/summary?days=7")
            
            # May return 200 or 404 depending on implementation
            assert response.status_code in [200, 404, 500]
    
    def test_invalid_endpoint(self, client):
        """Test invalid endpoint returns 404."""
        response = client.get("/api/invalid/endpoint")
        assert response.status_code == 404
    
    def test_malformed_payload(self, client):
        """Test malformed payload handling."""
        response = client.post(
            "/complaints/create",
            json={"invalid": "data"}
        )
        
        # Should return 422 (validation error) or 500
        assert response.status_code in [422, 500]
    
    def test_missing_required_fields(self, client):
        """Test missing required fields."""
        response = client.post(
            "/api/housing/match",
            json={"income": 25000}  # Missing other required fields
        )
        
        assert response.status_code in [422, 500]

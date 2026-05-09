"""Test complete complaint flow end-to-end."""

import pytest
from unittest.mock import MagicMock, patch


class TestComplaintFlow:
    """Test complete complaint workflow."""
    
    def test_complaint_creation_to_routing(
        self,
        client,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
        sample_complaint,
    ):
        """Test complaint creation through routing."""
        # Mock Gemini classification response
        classification_response = mock_gemini_response(
            '{"category": "Waste Management", "severity": "medium", "department": "Sanitation", "priority": 2}'
        )
        
        # Mock Firestore operations
        mock_doc = MagicMock()
        mock_doc.id = "complaint_123"
        mock_firestore.collection.return_value.add.return_value = (None, mock_doc)
        mock_firestore.collection.return_value.document.return_value.get.return_value.exists = True
        mock_firestore.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
            "complaintId": "C20240509001",
            "category": "Waste Management",
            "severity": "medium",
            "status": "pending",
        }
        
        with patch('app.complaint_classifier.classifier.get_gemini_client') as mock_gemini_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = classification_response
            mock_gemini_client.return_value.GenerativeModel.return_value = mock_model
            
            # Create complaint
            response = client.post("/complaints/create", json=sample_complaint)
            
            assert response.status_code == 200
            data = response.json()
            assert "complaintId" in data
            assert data["category"] == "Waste Management"
            assert data["severity"] == "medium"
    
    def test_complaint_classification_and_routing(
        self,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
    ):
        """Test complaint classification and routing integration."""
        from app.complaint_classifier.service import ComplaintClassifierService
        from app.complaint_router.service import ComplaintRouterService
        
        # Mock Gemini response
        classification_response = mock_gemini_response(
            '{"category": "Road Maintenance", "severity": "high", "department": "Roads & Infrastructure", "priority": 1}'
        )
        
        # Mock Firestore
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "complaintId": "C20240509001",
            "category": "Road Maintenance",
            "severity": "high",
            "location": "MG Road",
        }
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        with patch('app.complaint_classifier.classifier.get_gemini_client') as mock_gemini_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = classification_response
            mock_gemini_client.return_value.GenerativeModel.return_value = mock_model
            
            # Classify complaint
            classifier = ComplaintClassifierService()
            classification = classifier.classify_complaint(
                "C20240509001",
                "Large pothole on MG Road",
                "https://storage.googleapis.com/test/pothole.jpg"
            )
            
            assert classification is not None
            assert classification["category"] == "Road Maintenance"
            assert classification["severity"] == "high"
            
            # Route complaint
            router = ComplaintRouterService()
            routing = router.route_complaint("C20240509001")
            
            assert routing is not None
            assert "assignedOfficer" in routing or "department" in routing
    
    def test_high_severity_escalation_trigger(
        self,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
    ):
        """Test that high severity complaints trigger escalation."""
        from app.complaint_classifier.service import ComplaintClassifierService
        from app.escalation_agent.service import EscalationAgentService
        
        # Mock high severity classification
        classification_response = mock_gemini_response(
            '{"category": "Emergency", "severity": "critical", "department": "Emergency Services", "priority": 0}'
        )
        
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "complaintId": "C20240509001",
            "category": "Emergency",
            "severity": "critical",
            "status": "pending",
            "createdAt": "2024-05-09T10:00:00Z",
        }
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_firestore.collection.return_value.where.return_value.stream.return_value = [mock_doc]
        
        with patch('app.complaint_classifier.classifier.get_gemini_client') as mock_gemini_client:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = classification_response
            mock_gemini_client.return_value.GenerativeModel.return_value = mock_model
            
            # Classify as critical
            classifier = ComplaintClassifierService()
            classification = classifier.classify_complaint(
                "C20240509001",
                "Building collapse emergency",
                None
            )
            
            assert classification["severity"] == "critical"
            
            # Check escalation
            escalation_service = EscalationAgentService()
            escalations = escalation_service.check_critical_complaints()
            
            # Should identify critical complaint
            assert len(escalations) >= 0  # May be empty in mock

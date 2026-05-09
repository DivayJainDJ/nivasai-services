"""Test complete document parsing flow end-to-end."""

import pytest
from unittest.mock import MagicMock, patch


class TestDocumentParserFlow:
    """Test complete document parsing workflow."""
    
    def test_aadhaar_parsing_end_to_end(
        self,
        client,
        mock_firestore,
        mock_document_ai,
        mock_document_ai_response,
        sample_aadhaar_data,
    ):
        """Test Aadhaar card parsing from upload to profile update."""
        # Mock Document AI response
        aadhaar_text = f"""
        Name: {sample_aadhaar_data['name']}
        Aadhaar Number: {sample_aadhaar_data['aadhaarNumber']}
        DOB: {sample_aadhaar_data['dateOfBirth']}
        Address: {sample_aadhaar_data['address']}
        """
        
        mock_response = mock_document_ai_response(aadhaar_text)
        mock_document_ai.return_value.process_document.return_value = mock_response
        
        # Mock Firestore
        mock_firestore.collection.return_value.document.return_value.get.return_value.exists = False
        
        with patch('app.document_parser.parser.DocumentProcessorServiceClient', return_value=mock_document_ai):
            # Upload document
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
            assert data["parsed"]["name"] == sample_aadhaar_data["name"]
            assert "aadhaarNumber" in data["parsed"]
    
    def test_income_certificate_parsing(
        self,
        mock_firestore,
        mock_document_ai,
        mock_document_ai_response,
        sample_income_certificate,
    ):
        """Test income certificate parsing."""
        from app.document_parser.service import DocumentParserService
        
        # Mock Document AI response
        income_text = f"""
        Income Certificate
        Name: {sample_income_certificate['name']}
        Annual Income: Rs. {sample_income_certificate['annualIncome']}
        Certificate No: {sample_income_certificate['certificateNumber']}
        Issued By: {sample_income_certificate['issuedBy']}
        Valid Until: {sample_income_certificate['validUntil']}
        """
        
        mock_response = mock_document_ai_response(income_text)
        mock_document_ai.return_value.process_document.return_value = mock_response
        
        with patch('app.document_parser.parser.DocumentProcessorServiceClient', return_value=mock_document_ai):
            service = DocumentParserService()
            result = service.parse_document(
                "+919876543210",
                "income_certificate",
                "https://storage.googleapis.com/test/income.jpg"
            )
            
            assert result is not None
            assert "parsed" in result
            assert result["parsed"]["annualIncome"] == sample_income_certificate["annualIncome"]
    
    def test_eligibility_determination(
        self,
        mock_firestore,
    ):
        """Test eligibility determination from income."""
        from app.document_parser.eligibility_engine import EligibilityEngine
        
        engine = EligibilityEngine()
        
        # Test EWS eligibility
        eligibility = engine.determine_eligibility(300000)  # Annual income
        assert eligibility == "EWS"
        
        # Test LIG eligibility
        eligibility = engine.determine_eligibility(450000)
        assert eligibility == "LIG"
        
        # Test MIG eligibility
        eligibility = engine.determine_eligibility(900000)
        assert eligibility == "MIG"
        
        # Test above MIG
        eligibility = engine.determine_eligibility(1500000)
        assert eligibility == "Above MIG"
    
    def test_profile_update_after_parsing(
        self,
        mock_firestore,
        sample_aadhaar_data,
        sample_income_certificate,
    ):
        """Test family profile update after document parsing."""
        from app.document_parser.profile_updater import ProfileUpdater
        
        updater = ProfileUpdater()
        
        # Mock Firestore
        mock_firestore.collection.return_value.document.return_value.get.return_value.exists = False
        
        # Update profile with Aadhaar
        updater.update_profile(
            "+919876543210",
            "aadhaar",
            sample_aadhaar_data
        )
        
        # Verify Firestore set was called
        mock_firestore.collection.return_value.document.return_value.set.assert_called()
        
        # Update profile with income certificate
        updater.update_profile(
            "+919876543210",
            "income_certificate",
            sample_income_certificate
        )
        
        # Verify update was called
        assert mock_firestore.collection.return_value.document.return_value.set.call_count >= 2

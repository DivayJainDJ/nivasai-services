"""Tests for document extractor."""

import pytest

from app.document_parser.extractor import DocumentExtractor, ExtractionError


class TestAadhaarExtraction:
    """Test Aadhaar card extraction."""

    def setup_method(self):
        """Setup test fixtures."""
        self.extractor = DocumentExtractor()

    def test_extract_aadhaar_from_form_fields(self):
        """Test Aadhaar extraction from form fields."""
        parsed_data = {
            "text": "Sample text",
            "form_fields": {
                "Name": "Rajesh Kumar",
                "Aadhaar Number": "2345 6789 0123",
                "Address": "123 MG Road, Bangalore, Karnataka 560001",
                "DOB": "15/08/1985",
                "Gender": "Male",
            },
        }
        
        result = self.extractor.extract_aadhaar(parsed_data)
        assert result.fullName == "Rajesh Kumar"
        assert result.aadhaarNumber == "234567890123"
        assert "Bangalore" in result.address
        assert result.dateOfBirth == "15/08/1985"
        assert result.gender == "Male"

    def test_extract_aadhaar_from_text(self):
        """Test Aadhaar extraction from text."""
        parsed_data = {
            "text": """
            Name: Priya Sharma
            Aadhaar: 9876 5432 1098
            Address: 456 Park Street, Mumbai, Maharashtra 400001
            DOB: 20/03/1990
            Gender: Female
            """,
            "form_fields": {},
        }
        
        result = self.extractor.extract_aadhaar(parsed_data)
        assert result.fullName == "Priya Sharma"
        assert result.aadhaarNumber == "987654321098"
        assert "Mumbai" in result.address

    def test_extract_aadhaar_invalid_number(self):
        """Test Aadhaar extraction with invalid number."""
        parsed_data = {
            "text": "Name: Test User",
            "form_fields": {
                "Name": "Test User",
                "Aadhaar Number": "123456",  # Invalid
            },
        }
        
        with pytest.raises(ExtractionError):
            self.extractor.extract_aadhaar(parsed_data)


class TestIncomeCertificateExtraction:
    """Test income certificate extraction."""

    def setup_method(self):
        """Setup test fixtures."""
        self.extractor = DocumentExtractor()

    def test_extract_income_certificate(self):
        """Test income certificate extraction."""
        parsed_data = {
            "text": "Sample text",
            "form_fields": {
                "Citizen Name": "Amit Patel",
                "Annual Income": "Rs. 350000",
                "Issuing Authority": "Tehsildar Office, Ahmedabad",
                "Certificate Number": "INC/2024/12345",
            },
        }
        
        result = self.extractor.extract_income_certificate(parsed_data)
        assert result.citizenName == "Amit Patel"
        assert result.annualIncome == 350000
        assert "Tehsildar" in result.issuingAuthority
        assert result.certificateNumber == "INC/2024/12345"

    def test_extract_income_from_text(self):
        """Test income extraction from text."""
        parsed_data = {
            "text": """
            Citizen Name: Sunita Reddy
            Annual Income: Rs. 4,50,000
            Issued by: Revenue Department
            """,
            "form_fields": {},
        }
        
        result = self.extractor.extract_income_certificate(parsed_data)
        assert result.citizenName == "Sunita Reddy"
        assert result.annualIncome == 450000


class TestRationCardExtraction:
    """Test ration card extraction."""

    def setup_method(self):
        """Setup test fixtures."""
        self.extractor = DocumentExtractor()

    def test_extract_ration_card(self):
        """Test ration card extraction."""
        parsed_data = {
            "text": "Sample text",
            "form_fields": {
                "Family Head": "Ramesh Singh",
                "Total Members": "5",
                "Address": "789 Gandhi Nagar, Delhi 110001",
                "Card Type": "BPL",
            },
        }
        
        result = self.extractor.extract_ration_card(parsed_data)
        assert result.familyHead == "Ramesh Singh"
        assert result.familyCount == 5
        assert "Delhi" in result.address
        assert result.rationCardType == "BPL"

    def test_extract_ration_card_default_count(self):
        """Test ration card with missing family count."""
        parsed_data = {
            "text": "Family Head: Test User",
            "form_fields": {
                "Family Head": "Test User",
                "Address": "Test Address",
            },
        }
        
        result = self.extractor.extract_ration_card(parsed_data)
        assert result.familyCount == 1  # Default value

"""Tests for document validator."""

import pytest

from app.document_parser.validator import (
    ValidationException,
    clean_text,
    extract_numbers,
    mask_aadhaar,
    normalize_name,
    parse_income_amount,
    validate_aadhaar_number,
    validate_family_count,
    validate_income_range,
)


class TestAadhaarValidation:
    """Test Aadhaar number validation."""

    def test_valid_aadhaar(self):
        """Test valid Aadhaar numbers."""
        assert validate_aadhaar_number("234567890123") is True
        assert validate_aadhaar_number("9876 5432 1098") is True
        assert validate_aadhaar_number("2345-6789-0123") is True

    def test_invalid_aadhaar_length(self):
        """Test invalid Aadhaar length."""
        assert validate_aadhaar_number("12345") is False
        assert validate_aadhaar_number("12345678901234") is False

    def test_invalid_aadhaar_first_digit(self):
        """Test Aadhaar starting with 0 or 1."""
        assert validate_aadhaar_number("012345678901") is False
        assert validate_aadhaar_number("123456789012") is False

    def test_invalid_aadhaar_non_numeric(self):
        """Test non-numeric Aadhaar."""
        assert validate_aadhaar_number("ABCD12345678") is False
        assert validate_aadhaar_number("234567890ABC") is False

    def test_mask_aadhaar(self):
        """Test Aadhaar masking."""
        assert mask_aadhaar("234567890123") == "XXXX-XXXX-0123"
        assert mask_aadhaar("9876 5432 1098") == "XXXX-XXXX-1098"
        assert mask_aadhaar("invalid") == "XXXX-XXXX-XXXX"


class TestIncomeValidation:
    """Test income validation."""

    def test_valid_income(self):
        """Test valid income ranges."""
        assert validate_income_range(0) is True
        assert validate_income_range(300000) is True
        assert validate_income_range(600000) is True
        assert validate_income_range(10000000) is True

    def test_invalid_income(self):
        """Test invalid income ranges."""
        assert validate_income_range(-1) is False
        assert validate_income_range(10000001) is False

    def test_parse_income_amount(self):
        """Test income parsing."""
        assert parse_income_amount("300000") == 300000
        assert parse_income_amount("Rs. 300000") == 300000
        assert parse_income_amount("3,00,000") == 300000


class TestFamilyCountValidation:
    """Test family count validation."""

    def test_valid_family_count(self):
        """Test valid family counts."""
        assert validate_family_count(1) is True
        assert validate_family_count(5) is True
        assert validate_family_count(20) is True

    def test_invalid_family_count(self):
        """Test invalid family counts."""
        assert validate_family_count(0) is False
        assert validate_family_count(21) is False
        assert validate_family_count(-1) is False


class TestTextCleaning:
    """Test text cleaning utilities."""

    def test_clean_text(self):
        """Test text cleaning."""
        assert clean_text("  Hello   World  ") == "Hello World"
        assert clean_text("Test@#$%Text") == "TestText"

    def test_extract_numbers(self):
        """Test number extraction."""
        assert extract_numbers("ABC123DEF456") == "123456"
        assert extract_numbers("Rs. 300000") == "300000"

    def test_normalize_name(self):
        """Test name normalization."""
        assert normalize_name("john doe") == "John Doe"
        assert normalize_name("  JANE   SMITH  ") == "Jane Smith"

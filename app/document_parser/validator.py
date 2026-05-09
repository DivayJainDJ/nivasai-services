"""Validation utilities for document parser."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from app.document_parser.schemas import (
    AadhaarData,
    IncomeCertificateData,
    RationCardData,
)


class ValidationException(Exception):
    """Raised when validation fails."""


def validate_aadhaar_number(aadhaar: str) -> bool:
    """Validate Aadhaar number format."""
    # Remove spaces and hyphens
    cleaned = aadhaar.replace(" ", "").replace("-", "")
    
    # Must be 12 digits
    if not cleaned.isdigit() or len(cleaned) != 12:
        return False
    
    # First digit cannot be 0 or 1
    if cleaned[0] in ["0", "1"]:
        return False
    
    return True


def mask_aadhaar(aadhaar: str) -> str:
    """Mask Aadhaar number for security."""
    cleaned = aadhaar.replace(" ", "").replace("-", "")
    if len(cleaned) == 12:
        return f"XXXX-XXXX-{cleaned[-4:]}"
    return "XXXX-XXXX-XXXX"


def validate_income_range(income: int) -> bool:
    """Validate income is in reasonable range."""
    return 0 <= income <= 10000000  # 0 to 1 crore


def validate_family_count(count: int) -> bool:
    """Validate family count is reasonable."""
    return 1 <= count <= 20


def validate_aadhaar_data(data: dict[str, Any]) -> AadhaarData:
    """Validate extracted Aadhaar data."""
    try:
        return AadhaarData.model_validate(data)
    except ValidationError as exc:
        raise ValidationException(f"Invalid Aadhaar data: {exc}") from exc


def validate_income_certificate_data(data: dict[str, Any]) -> IncomeCertificateData:
    """Validate extracted income certificate data."""
    try:
        return IncomeCertificateData.model_validate(data)
    except ValidationError as exc:
        raise ValidationException(f"Invalid income certificate data: {exc}") from exc


def validate_ration_card_data(data: dict[str, Any]) -> RationCardData:
    """Validate extracted ration card data."""
    try:
        return RationCardData.model_validate(data)
    except ValidationError as exc:
        raise ValidationException(f"Invalid ration card data: {exc}") from exc


def clean_text(text: str) -> str:
    """Clean extracted text."""
    # Remove extra whitespace
    text = " ".join(text.split())
    # Remove special characters but keep basic punctuation
    text = re.sub(r"[^\w\s.,/-]", "", text)
    return text.strip()


def extract_numbers(text: str) -> str:
    """Extract only numbers from text."""
    return "".join(c for c in text if c.isdigit())


def parse_income_amount(text: str) -> int:
    """Parse income amount from text."""
    # Extract numbers
    numbers = extract_numbers(text)
    
    if not numbers:
        raise ValidationException("No income amount found")
    
    try:
        income = int(numbers)
        if not validate_income_range(income):
            raise ValidationException(f"Income {income} out of valid range")
        return income
    except ValueError as exc:
        raise ValidationException(f"Invalid income format: {text}") from exc


def normalize_name(name: str) -> str:
    """Normalize person name."""
    # Remove extra spaces
    name = " ".join(name.split())
    # Title case
    name = name.title()
    # Remove special characters
    name = re.sub(r"[^\w\s.-]", "", name)
    return name.strip()


def validate_document_type(doc_type: str) -> bool:
    """Validate document type."""
    valid_types = ["aadhaar", "income_certificate", "ration_card"]
    return doc_type.lower() in valid_types

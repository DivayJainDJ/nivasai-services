"""Pydantic schemas for document parser."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AadhaarData(BaseModel):
    """Extracted Aadhaar card data."""

    fullName: str = Field(min_length=2, max_length=100)
    aadhaarNumber: str = Field(min_length=12, max_length=12)
    address: str = Field(min_length=5, max_length=500)
    dateOfBirth: Optional[str] = None
    gender: Optional[str] = None

    @field_validator("aadhaarNumber")
    @classmethod
    def validate_aadhaar(cls, value: str) -> str:
        """Validate Aadhaar number format."""
        # Remove spaces and validate
        cleaned = value.replace(" ", "").replace("-", "")
        if not cleaned.isdigit() or len(cleaned) != 12:
            raise ValueError("Invalid Aadhaar number format")
        return cleaned


class IncomeCertificateData(BaseModel):
    """Extracted income certificate data."""

    citizenName: str = Field(min_length=2, max_length=100)
    annualIncome: int = Field(ge=0, le=10000000)
    issuingAuthority: str = Field(min_length=2, max_length=200)
    certificateNumber: Optional[str] = None
    issueDate: Optional[str] = None


class RationCardData(BaseModel):
    """Extracted ration card data."""

    familyHead: str = Field(min_length=2, max_length=100)
    familyCount: int = Field(ge=1, le=20)
    address: str = Field(min_length=5, max_length=500)
    rationCardType: Optional[str] = None
    cardNumber: Optional[str] = None
    memberNames: list[str] = Field(default_factory=list)


class EligibilityResult(BaseModel):
    """Eligibility determination result."""

    category: Literal["EWS", "LIG", "MIG", "Not Eligible"]
    annualIncome: int
    isEligible: bool
    eligibleSchemes: list[str] = Field(default_factory=list)
    reason: str


class FamilyProfile(BaseModel):
    """Family profile document."""

    citizenId: str
    name: str
    annualIncome: int = 0
    familyCount: int = 1
    address: str = ""
    aadhaarNumber: Optional[str] = None
    eligibilityCategory: Optional[str] = None
    documentsVerified: bool = False
    verifiedDocuments: list[str] = Field(default_factory=list)
    lastUpdated: Optional[datetime] = None


class DocumentUploadRequest(BaseModel):
    """Document upload request."""

    citizenId: str = Field(min_length=5, max_length=100)
    documentType: Literal["aadhaar", "income_certificate", "ration_card"]


class DocumentParseResponse(BaseModel):
    """Document parsing response."""

    success: bool
    citizenId: str
    documentType: str
    eligibilityCategory: Optional[str] = None
    parsedData: dict
    verified: bool
    message: str

"""Document parser agent for government document verification."""

from app.document_parser.eligibility_engine import EligibilityEngine
from app.document_parser.extractor import DocumentExtractor
from app.document_parser.parser import DocumentAIParser
from app.document_parser.profile_updater import ProfileUpdater
from app.document_parser.schemas import (
    AadhaarData,
    DocumentParseResponse,
    DocumentUploadRequest,
    EligibilityResult,
    FamilyProfile,
    IncomeCertificateData,
    RationCardData,
)
from app.document_parser.service import DocumentParserService
from app.document_parser.trigger import start_document_trigger, stop_document_trigger
from app.document_parser.validator import (
    mask_aadhaar,
    validate_aadhaar_number,
    validate_document_type,
)

__all__ = [
    "DocumentParserService",
    "DocumentAIParser",
    "DocumentExtractor",
    "EligibilityEngine",
    "ProfileUpdater",
    "AadhaarData",
    "IncomeCertificateData",
    "RationCardData",
    "EligibilityResult",
    "FamilyProfile",
    "DocumentUploadRequest",
    "DocumentParseResponse",
    "start_document_trigger",
    "stop_document_trigger",
    "validate_aadhaar_number",
    "validate_document_type",
    "mask_aadhaar",
]

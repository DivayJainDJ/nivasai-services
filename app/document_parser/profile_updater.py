"""Update family profiles in Firestore after document verification."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from firebase_admin import firestore

from app.document_parser.schemas import (
    AadhaarData,
    FamilyProfile,
    IncomeCertificateData,
    RationCardData,
)
from app.document_parser.validator import mask_aadhaar
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ProfileUpdateError(Exception):
    """Raised when profile update fails."""


class ProfileUpdater:
    """Update family profiles in Firestore."""

    def __init__(self):
        """Initialize profile updater."""
        self.db = db
        self.profiles_collection = "family_profiles"

    def update_from_aadhaar(
        self,
        citizen_id: str,
        aadhaar_data: AadhaarData,
    ) -> FamilyProfile:
        """Update profile with Aadhaar data."""
        profile_ref = self.db.collection(self.profiles_collection).document(citizen_id)
        
        # Get existing profile or create new
        profile_doc = profile_ref.get()
        
        if profile_doc.exists:
            profile_data = profile_doc.to_dict()
        else:
            profile_data = {
                "citizenId": citizen_id,
                "name": "",
                "annualIncome": 0,
                "familyCount": 1,
                "address": "",
                "documentsVerified": False,
                "verifiedDocuments": [],
            }
        
        # Update with Aadhaar data
        profile_data.update({
            "name": aadhaar_data.fullName,
            "address": aadhaar_data.address,
            "aadhaarNumber": aadhaar_data.aadhaarNumber,
            "lastUpdated": firestore.SERVER_TIMESTAMP,
        })
        
        # Add to verified documents
        verified_docs = profile_data.get("verifiedDocuments", [])
        if "aadhaar" not in verified_docs:
            verified_docs.append("aadhaar")
        profile_data["verifiedDocuments"] = verified_docs
        
        # Save to Firestore
        profile_ref.set(profile_data, merge=True)
        
        logger.info(
            "profile_updated_aadhaar",
            citizen_id=citizen_id,
            name=aadhaar_data.fullName,
            aadhaar_masked=mask_aadhaar(aadhaar_data.aadhaarNumber),
        )
        
        return FamilyProfile(**profile_data)

    def update_from_income_certificate(
        self,
        citizen_id: str,
        income_data: IncomeCertificateData,
        eligibility_category: Optional[str] = None,
    ) -> FamilyProfile:
        """Update profile with income certificate data."""
        profile_ref = self.db.collection(self.profiles_collection).document(citizen_id)
        
        # Get existing profile or create new
        profile_doc = profile_ref.get()
        
        if profile_doc.exists:
            profile_data = profile_doc.to_dict()
        else:
            profile_data = {
                "citizenId": citizen_id,
                "name": "",
                "annualIncome": 0,
                "familyCount": 1,
                "address": "",
                "documentsVerified": False,
                "verifiedDocuments": [],
            }
        
        # Update with income data
        profile_data.update({
            "name": income_data.citizenName,
            "annualIncome": income_data.annualIncome,
            "lastUpdated": firestore.SERVER_TIMESTAMP,
        })
        
        # Update eligibility if provided
        if eligibility_category:
            profile_data["eligibilityCategory"] = eligibility_category
            profile_data["documentsVerified"] = True
        
        # Add to verified documents
        verified_docs = profile_data.get("verifiedDocuments", [])
        if "income_certificate" not in verified_docs:
            verified_docs.append("income_certificate")
        profile_data["verifiedDocuments"] = verified_docs
        
        # Save to Firestore
        profile_ref.set(profile_data, merge=True)
        
        logger.info(
            "profile_updated_income",
            citizen_id=citizen_id,
            name=income_data.citizenName,
            income=income_data.annualIncome,
            category=eligibility_category,
        )
        
        return FamilyProfile(**profile_data)

    def update_from_ration_card(
        self,
        citizen_id: str,
        ration_data: RationCardData,
    ) -> FamilyProfile:
        """Update profile with ration card data."""
        profile_ref = self.db.collection(self.profiles_collection).document(citizen_id)
        
        # Get existing profile or create new
        profile_doc = profile_ref.get()
        
        if profile_doc.exists:
            profile_data = profile_doc.to_dict()
        else:
            profile_data = {
                "citizenId": citizen_id,
                "name": "",
                "annualIncome": 0,
                "familyCount": 1,
                "address": "",
                "documentsVerified": False,
                "verifiedDocuments": [],
            }
        
        # Update with ration card data
        profile_data.update({
            "name": ration_data.familyHead,
            "familyCount": ration_data.familyCount,
            "address": ration_data.address,
            "rationCardType": ration_data.rationCardType,
            "lastUpdated": firestore.SERVER_TIMESTAMP,
        })
        
        # Add to verified documents
        verified_docs = profile_data.get("verifiedDocuments", [])
        if "ration_card" not in verified_docs:
            verified_docs.append("ration_card")
        profile_data["verifiedDocuments"] = verified_docs
        
        # Save to Firestore
        profile_ref.set(profile_data, merge=True)
        
        logger.info(
            "profile_updated_ration",
            citizen_id=citizen_id,
            family_head=ration_data.familyHead,
            family_count=ration_data.familyCount,
        )
        
        return FamilyProfile(**profile_data)

    def get_profile(self, citizen_id: str) -> Optional[FamilyProfile]:
        """Get existing family profile."""
        profile_ref = self.db.collection(self.profiles_collection).document(citizen_id)
        profile_doc = profile_ref.get()
        
        if not profile_doc.exists:
            return None
        
        profile_data = profile_doc.to_dict()
        return FamilyProfile(**profile_data)

    def mark_documents_verified(self, citizen_id: str) -> None:
        """Mark all documents as verified."""
        profile_ref = self.db.collection(self.profiles_collection).document(citizen_id)
        profile_ref.update({
            "documentsVerified": True,
            "lastUpdated": firestore.SERVER_TIMESTAMP,
        })
        
        logger.info("documents_verified", citizen_id=citizen_id)

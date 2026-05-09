"""Main document parser service orchestration."""

from __future__ import annotations

from typing import Optional

from app.document_parser.eligibility_engine import EligibilityEngine
from app.document_parser.extractor import DocumentExtractor, ExtractionError
from app.document_parser.parser import DocumentAIParser, DocumentParserError
from app.document_parser.profile_updater import ProfileUpdater, ProfileUpdateError
from app.document_parser.schemas import (
    AadhaarData,
    DocumentParseResponse,
    IncomeCertificateData,
    RationCardData,
)
from app.document_parser.validator import (
    ValidationException,
    mask_aadhaar,
    validate_aadhaar_data,
    validate_document_type,
    validate_income_certificate_data,
    validate_ration_card_data,
)
from app.shared.firestore.client import bucket, db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class DocumentParserService:
    """Main service for document parsing and verification."""

    def __init__(self):
        """Initialize document parser service."""
        self.parser = DocumentAIParser()
        self.extractor = DocumentExtractor()
        self.eligibility_engine = EligibilityEngine()
        self.profile_updater = ProfileUpdater()
        self.db = db
        self.bucket = bucket

    async def process_document(
        self,
        citizen_id: str,
        document_type: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> DocumentParseResponse:
        """
        Process uploaded document end-to-end.
        
        Steps:
        1. Validate document type
        2. Upload to Cloud Storage
        3. Parse with Document AI
        4. Extract structured data
        5. Validate extracted data
        6. Determine eligibility (for income certificates)
        7. Update family profile
        8. Update Firestore document status
        9. Return response
        """
        try:
            # Validate document type
            if not validate_document_type(document_type):
                return DocumentParseResponse(
                    success=False,
                    citizenId=citizen_id,
                    documentType=document_type,
                    parsedData={},
                    verified=False,
                    message=f"Invalid document type: {document_type}",
                )
            
            logger.info(
                "document_processing_started",
                citizen_id=citizen_id,
                document_type=document_type,
                size=len(image_bytes),
            )
            
            # Create Firestore document
            doc_id = await self._create_document_record(citizen_id, document_type)
            
            # Upload to Cloud Storage
            document_url = await self._upload_to_storage(
                citizen_id,
                document_type,
                image_bytes,
                mime_type,
            )
            
            # Update document with URL
            await self._update_document_url(doc_id, document_url)
            
            # Parse document with Document AI
            try:
                parsed_data = self.parser.parse_document(image_bytes, mime_type)
            except DocumentParserError as exc:
                logger.error("document_parsing_failed", error=str(exc))
                await self._mark_document_failed(doc_id, str(exc))
                return DocumentParseResponse(
                    success=False,
                    citizenId=citizen_id,
                    documentType=document_type,
                    parsedData={},
                    verified=False,
                    message=f"Document parsing failed: {exc}",
                )
            
            # Extract and validate based on document type
            try:
                if document_type == "aadhaar":
                    result = await self._process_aadhaar(
                        citizen_id,
                        parsed_data,
                        doc_id,
                    )
                elif document_type == "income_certificate":
                    result = await self._process_income_certificate(
                        citizen_id,
                        parsed_data,
                        doc_id,
                    )
                elif document_type == "ration_card":
                    result = await self._process_ration_card(
                        citizen_id,
                        parsed_data,
                        doc_id,
                    )
                else:
                    raise ValidationException(f"Unsupported document type: {document_type}")
                
                logger.info(
                    "document_processing_completed",
                    citizen_id=citizen_id,
                    document_type=document_type,
                    verified=result.verified,
                )
                
                return result
            
            except (ExtractionError, ValidationException) as exc:
                logger.error("document_extraction_failed", error=str(exc))
                await self._mark_document_failed(doc_id, str(exc))
                return DocumentParseResponse(
                    success=False,
                    citizenId=citizen_id,
                    documentType=document_type,
                    parsedData={},
                    verified=False,
                    message=f"Data extraction failed: {exc}",
                )
        
        except Exception as exc:
            logger.error(
                "document_processing_error",
                citizen_id=citizen_id,
                error=str(exc),
            )
            return DocumentParseResponse(
                success=False,
                citizenId=citizen_id,
                documentType=document_type,
                parsedData={},
                verified=False,
                message=f"Processing error: {exc}",
            )

    async def _process_aadhaar(
        self,
        citizen_id: str,
        parsed_data: dict,
        doc_id: str,
    ) -> DocumentParseResponse:
        """Process Aadhaar card."""
        # Extract data
        aadhaar_data = self.extractor.extract_aadhaar(parsed_data)
        
        # Validate
        validated_data = validate_aadhaar_data(aadhaar_data.model_dump())
        
        # Update family profile
        try:
            self.profile_updater.update_from_aadhaar(citizen_id, validated_data)
        except ProfileUpdateError as exc:
            logger.error("profile_update_failed", error=str(exc))
        
        # Mark document as processed
        await self._mark_document_processed(
            doc_id,
            validated_data.model_dump(),
        )
        
        # Prepare response (mask Aadhaar)
        response_data = validated_data.model_dump()
        response_data["aadhaarNumber"] = mask_aadhaar(validated_data.aadhaarNumber)
        
        return DocumentParseResponse(
            success=True,
            citizenId=citizen_id,
            documentType="aadhaar",
            parsedData=response_data,
            verified=True,
            message="Aadhaar card verified successfully",
        )

    async def _process_income_certificate(
        self,
        citizen_id: str,
        parsed_data: dict,
        doc_id: str,
    ) -> DocumentParseResponse:
        """Process income certificate."""
        # Extract data
        income_data = self.extractor.extract_income_certificate(parsed_data)
        
        # Validate
        validated_data = validate_income_certificate_data(income_data.model_dump())
        
        # Determine eligibility
        eligibility = self.eligibility_engine.determine_eligibility(
            validated_data.annualIncome,
        )
        
        # Update family profile
        try:
            self.profile_updater.update_from_income_certificate(
                citizen_id,
                validated_data,
                eligibility.category,
            )
        except ProfileUpdateError as exc:
            logger.error("profile_update_failed", error=str(exc))
        
        # Mark document as processed
        await self._mark_document_processed(
            doc_id,
            validated_data.model_dump(),
            eligibility.category,
        )
        
        # Prepare response
        response_data = validated_data.model_dump()
        response_data["eligibility"] = eligibility.model_dump()
        
        return DocumentParseResponse(
            success=True,
            citizenId=citizen_id,
            documentType="income_certificate",
            eligibilityCategory=eligibility.category,
            parsedData=response_data,
            verified=True,
            message=f"Income certificate verified. Category: {eligibility.category}",
        )

    async def _process_ration_card(
        self,
        citizen_id: str,
        parsed_data: dict,
        doc_id: str,
    ) -> DocumentParseResponse:
        """Process ration card."""
        # Extract data
        ration_data = self.extractor.extract_ration_card(parsed_data)
        
        # Validate
        validated_data = validate_ration_card_data(ration_data.model_dump())
        
        # Update family profile
        try:
            self.profile_updater.update_from_ration_card(citizen_id, validated_data)
        except ProfileUpdateError as exc:
            logger.error("profile_update_failed", error=str(exc))
        
        # Mark document as processed
        await self._mark_document_processed(
            doc_id,
            validated_data.model_dump(),
        )
        
        return DocumentParseResponse(
            success=True,
            citizenId=citizen_id,
            documentType="ration_card",
            parsedData=validated_data.model_dump(),
            verified=True,
            message="Ration card verified successfully",
        )

    async def _create_document_record(
        self,
        citizen_id: str,
        document_type: str,
    ) -> str:
        """Create initial document record in Firestore."""
        doc_ref = self.db.collection("citizen_documents").document()
        doc_ref.set({
            "citizenId": citizen_id,
            "documentType": document_type,
            "status": "processing",
            "parsed": False,
            "verified": False,
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
        return doc_ref.id

    async def _upload_to_storage(
        self,
        citizen_id: str,
        document_type: str,
        image_bytes: bytes,
        mime_type: str,
    ) -> str:
        """Upload document to Cloud Storage."""
        from datetime import datetime
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"documents/{citizen_id}/{document_type}_{timestamp}.jpg"
        
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)
        
        # Make publicly readable (optional - adjust based on security requirements)
        # blob.make_public()
        
        logger.info("document_uploaded", blob_name=blob_name)
        
        return blob.public_url if blob.public_url else blob_name

    async def _update_document_url(self, doc_id: str, document_url: str) -> None:
        """Update document with storage URL."""
        doc_ref = self.db.collection("citizen_documents").document(doc_id)
        doc_ref.update({"documentUrl": document_url})

    async def _mark_document_processed(
        self,
        doc_id: str,
        extracted_data: dict,
        eligibility_category: Optional[str] = None,
    ) -> None:
        """Mark document as successfully processed."""
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        
        update_data = {
            "status": "completed",
            "parsed": True,
            "verified": True,
            "extractedData": extracted_data,
            "processedAt": SERVER_TIMESTAMP,
        }
        
        if eligibility_category:
            update_data["eligibilityCategory"] = eligibility_category
        
        doc_ref = self.db.collection("citizen_documents").document(doc_id)
        doc_ref.update(update_data)

    async def _mark_document_failed(self, doc_id: str, error: str) -> None:
        """Mark document as failed."""
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        
        doc_ref = self.db.collection("citizen_documents").document(doc_id)
        doc_ref.update({
            "status": "failed",
            "error": error,
            "processedAt": SERVER_TIMESTAMP,
        })


# Import firestore for SERVER_TIMESTAMP
from firebase_admin import firestore

"""Document upload API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.document_parser.schemas import DocumentParseResponse
from app.document_parser.service import DocumentParserService
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/upload-document", response_model=DocumentParseResponse)
async def upload_document(
    documentImage: UploadFile = File(..., description="Document image file"),
    documentType: str = Form(..., description="Type: aadhaar, income_certificate, ration_card"),
    citizenId: str = Form(..., description="Citizen ID"),
) -> DocumentParseResponse:
    """
    Upload and process government document.
    
    Supported document types:
    - aadhaar: Aadhaar card
    - income_certificate: Income certificate
    - ration_card: Ration card
    
    Returns:
    - Parsed and validated document data
    - Eligibility category (for income certificates)
    - Verification status
    """
    try:
        # Validate inputs
        if not citizenId or len(citizenId) < 5:
            raise HTTPException(
                status_code=400,
                detail="Invalid citizenId. Must be at least 5 characters.",
            )
        
        valid_types = ["aadhaar", "income_certificate", "ration_card"]
        if documentType not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid documentType. Must be one of: {', '.join(valid_types)}",
            )
        
        # Read image bytes
        image_bytes = await documentImage.read()
        
        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty document image",
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Document image too large. Maximum size: {max_size / 1024 / 1024}MB",
            )
        
        # Determine MIME type
        mime_type = documentImage.content_type or "image/jpeg"
        if not mime_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Must be an image.",
            )
        
        logger.info(
            "document_upload_received",
            citizen_id=citizenId,
            document_type=documentType,
            size=len(image_bytes),
            mime_type=mime_type,
        )
        
        # Process document
        service = DocumentParserService()
        result = await service.process_document(
            citizen_id=citizenId,
            document_type=documentType,
            image_bytes=image_bytes,
            mime_type=mime_type,
        )
        
        if not result.success:
            logger.warning(
                "document_processing_failed",
                citizen_id=citizenId,
                message=result.message,
            )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as exc:
        logger.error(
            "document_upload_error",
            citizen_id=citizenId if 'citizenId' in locals() else "unknown",
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(exc)}",
        ) from exc


@router.get("/document-status/{citizen_id}")
async def get_document_status(citizen_id: str) -> dict:
    """
    Get document processing status for a citizen.
    
    Returns list of all documents and their verification status.
    """
    try:
        from app.shared.firestore.client import db
        
        # Query documents for citizen
        docs_ref = db.collection("citizen_documents").where("citizenId", "==", citizen_id)
        docs = docs_ref.stream()
        
        documents = []
        for doc in docs:
            doc_data = doc.to_dict()
            documents.append({
                "documentId": doc.id,
                "documentType": doc_data.get("documentType"),
                "status": doc_data.get("status"),
                "verified": doc_data.get("verified", False),
                "createdAt": doc_data.get("createdAt"),
                "processedAt": doc_data.get("processedAt"),
            })
        
        return {
            "citizenId": citizen_id,
            "documents": documents,
            "totalDocuments": len(documents),
        }
    
    except Exception as exc:
        logger.error("document_status_error", citizen_id=citizen_id, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch document status: {str(exc)}",
        ) from exc

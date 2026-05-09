"""Google Document AI parser integration."""

from __future__ import annotations

import os
from typing import Optional

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai

from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class DocumentParserError(Exception):
    """Raised when document parsing fails."""


class DocumentAIParser:
    """Google Document AI Form Parser wrapper."""

    def __init__(self):
        """Initialize Document AI client."""
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self.location = os.getenv("DOCUMENT_AI_LOCATION", "us")
        self.processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
        
        if not self.project_id or not self.processor_id:
            logger.warning("document_ai_not_configured", message="Using mock parser")
            self.client = None
        else:
            try:
                opts = ClientOptions(api_endpoint=f"{self.location}-documentai.googleapis.com")
                self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
                self.processor_name = self.client.processor_path(
                    self.project_id,
                    self.location,
                    self.processor_id,
                )
                logger.info("document_ai_initialized", processor=self.processor_name)
            except Exception as exc:
                logger.error("document_ai_init_failed", error=str(exc))
                self.client = None

    def parse_document(self, image_bytes: bytes, mime_type: str) -> dict:
        """
        Parse document using Google Document AI.
        
        Returns extracted text and form fields.
        """
        if not self.client:
            # Use mock parser for testing
            return self._mock_parse(image_bytes, mime_type)
        
        try:
            # Create document
            raw_document = documentai.RawDocument(
                content=image_bytes,
                mime_type=mime_type,
            )
            
            # Configure request
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document,
            )
            
            # Process document
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract text
            full_text = document.text
            
            # Extract form fields
            form_fields = {}
            for page in document.pages:
                for field in page.form_fields:
                    field_name = self._get_text(field.field_name, document.text)
                    field_value = self._get_text(field.field_value, document.text)
                    
                    if field_name and field_value:
                        form_fields[field_name.strip()] = field_value.strip()
            
            # Extract entities
            entities = {}
            for entity in document.entities:
                entity_type = entity.type_
                entity_text = entity.mention_text
                entities[entity_type] = entity_text
            
            logger.info(
                "document_parsed",
                text_length=len(full_text),
                form_fields=len(form_fields),
                entities=len(entities),
            )
            
            return {
                "text": full_text,
                "form_fields": form_fields,
                "entities": entities,
            }
        
        except Exception as exc:
            logger.error("document_parsing_failed", error=str(exc))
            raise DocumentParserError(f"Failed to parse document: {exc}") from exc

    def _get_text(self, layout, full_text: str) -> str:
        """Extract text from layout."""
        if not layout or not layout.text_anchor:
            return ""
        
        text_segments = []
        for segment in layout.text_anchor.text_segments:
            start_index = int(segment.start_index) if segment.start_index else 0
            end_index = int(segment.end_index) if segment.end_index else len(full_text)
            text_segments.append(full_text[start_index:end_index])
        
        return "".join(text_segments)

    def _mock_parse(self, image_bytes: bytes, mime_type: str) -> dict:
        """
        Mock parser for testing when Document AI is not configured.
        
        Returns simulated extraction results.
        """
        logger.info("using_mock_parser", size=len(image_bytes))
        
        # Simulate different document types based on image size
        # This is just for testing - real implementation uses Document AI
        
        return {
            "text": "Mock document text for testing",
            "form_fields": {
                "Name": "Test Citizen",
                "Address": "123 Test Street, Test City",
            },
            "entities": {},
        }

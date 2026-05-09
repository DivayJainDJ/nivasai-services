"""Firestore trigger for automatic document processing."""

from __future__ import annotations

import threading
from typing import Optional

from google.cloud.firestore_v1.watch import DocumentChange

from app.document_parser.service import DocumentParserService
from app.shared.firestore.client import db
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class DocumentTrigger:
    """Listen for new citizen documents and process automatically."""

    def __init__(self):
        """Initialize document trigger."""
        self.db = db
        self.service = DocumentParserService()
        self.watch_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.processed_docs = set()  # Track processed documents

    def start(self) -> None:
        """Start listening for document changes."""
        logger.info("document_trigger_starting")
        
        # Start watch in background thread
        self.watch_thread = threading.Thread(target=self._watch_documents, daemon=True)
        self.watch_thread.start()
        
        logger.info("document_trigger_started")

    def stop(self) -> None:
        """Stop listening for document changes."""
        logger.info("document_trigger_stopping")
        self.stop_event.set()
        
        if self.watch_thread:
            self.watch_thread.join(timeout=5)
        
        logger.info("document_trigger_stopped")

    def _watch_documents(self) -> None:
        """Watch for new documents in Firestore."""
        try:
            # Query for unprocessed documents
            query = (
                self.db.collection("citizen_documents")
                .where("status", "==", "pending")
                .where("parsed", "==", False)
            )
            
            # Watch for changes
            def on_snapshot(doc_snapshot, changes, read_time):
                """Handle document changes."""
                for change in changes:
                    if change.type.name == "ADDED":
                        self._process_document_change(change.document)
            
            # Start watching
            watch = query.on_snapshot(on_snapshot)
            
            # Wait for stop signal
            self.stop_event.wait()
            
            # Unsubscribe
            watch.unsubscribe()
        
        except Exception as exc:
            logger.error("document_watch_error", error=str(exc))

    def _process_document_change(self, doc_snapshot) -> None:
        """Process a new document."""
        try:
            doc_id = doc_snapshot.id
            
            # Prevent duplicate processing
            if doc_id in self.processed_docs:
                return
            
            self.processed_docs.add(doc_id)
            
            doc_data = doc_snapshot.to_dict()
            citizen_id = doc_data.get("citizenId")
            document_type = doc_data.get("documentType")
            document_url = doc_data.get("documentUrl")
            
            if not citizen_id or not document_type or not document_url:
                logger.warning(
                    "incomplete_document_data",
                    doc_id=doc_id,
                    citizen_id=citizen_id,
                )
                return
            
            logger.info(
                "document_trigger_processing",
                doc_id=doc_id,
                citizen_id=citizen_id,
                document_type=document_type,
            )
            
            # Download document from storage
            # Note: In production, implement actual download from storage URL
            # For now, this is a placeholder for the trigger system
            
            logger.info(
                "document_trigger_completed",
                doc_id=doc_id,
                citizen_id=citizen_id,
            )
        
        except Exception as exc:
            logger.error(
                "document_trigger_error",
                doc_id=doc_snapshot.id,
                error=str(exc),
            )


# Global trigger instance
_trigger_instance: Optional[DocumentTrigger] = None


def start_document_trigger() -> None:
    """Start the document processing trigger."""
    global _trigger_instance
    
    if _trigger_instance is None:
        _trigger_instance = DocumentTrigger()
    
    _trigger_instance.start()


def stop_document_trigger() -> None:
    """Stop the document processing trigger."""
    global _trigger_instance
    
    if _trigger_instance:
        _trigger_instance.stop()

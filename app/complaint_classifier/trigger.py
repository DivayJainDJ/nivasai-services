"""
Complaint classification trigger and event handling
Handles Firestore triggers and event processing
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import json

from app.complaint_classifier.service import get_complaint_classifier
from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger
from app.shared.pubsub.publisher import publish_event
from app.shared.schemas.complaint import ComplaintStatus

logger = get_logger(__name__)


class ComplaintTriggerHandler:
    """Handles complaint-related triggers and events"""
    
    def __init__(self):
        self.classifier = None
        self.firestore = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize trigger handler"""
        self.classifier = await get_complaint_classifier()
        self.firestore = await get_firestore_client()
        self._initialized = True
        logger.info("ComplaintTriggerHandler initialized")
    
    async def handle_complaint_created(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle complaint creation event
        Triggered when a new complaint is created in Firestore
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Extract complaint data from event
            complaint_data = self._extract_complaint_data(event_data)
            complaint_id = complaint_data.get('id')
            
            if not complaint_id:
                raise ValueError("Complaint ID not found in event data")
            
            logger.info(
                "Processing complaint creation trigger",
                complaint_id=complaint_id,
                has_image=bool(complaint_data.get('image_url'))
            )
            
            # Classify the complaint
            classification = await self.classifier.classify_complaint(
                complaint_id=complaint_id,
                description=complaint_data.get('description', ''),
                image_url=complaint_data.get('image_url'),
                metadata={
                    'user_id': complaint_data.get('user_id'),
                    'location': complaint_data.get('location'),
                    'ward_id': complaint_data.get('location', {}).get('ward_id'),
                    'trigger_type': 'complaint_created'
                }
            )
            
            # Update complaint with classification
            await self._update_complaint_classification(complaint_id, classification)
            
            # Update complaint status
            await self._update_complaint_status(complaint_id, ComplaintStatus.CLASSIFIED)
            
            # Publish classification event for routing
            await self._publish_classification_event(complaint_id, classification, complaint_data)
            
            # Log business event
            await self._log_business_event(
                event_type='complaint_classified',
                complaint_id=complaint_id,
                classification_data=classification.dict(),
                metadata=complaint_data
            )
            
            logger.info(
                "Complaint classification completed",
                complaint_id=complaint_id,
                category=classification.category,
                severity=classification.severity,
                confidence=classification.confidence
            )
            
            return {
                'success': True,
                'complaint_id': complaint_id,
                'classification': classification.dict(),
                'next_action': 'routing'
            }
            
        except Exception as e:
            logger.error(
                "Complaint classification trigger failed",
                error=str(e),
                error_type=type(e).__name__,
                event_data=event_data
            )
            
            # Update complaint status to failed
            if 'complaint_id' in locals():
                await self._update_complaint_status(
                    locals()['complaint_id'], 
                    ComplaintStatus.PENDING,
                    error=str(e)
                )
            
            raise
    
    async def handle_complaint_updated(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle complaint update event
        Triggered when a complaint is updated in Firestore
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Extract complaint data
            complaint_data = self._extract_complaint_data(event_data)
            complaint_id = complaint_data.get('id')
            
            if not complaint_id:
                raise ValueError("Complaint ID not found in event data")
            
            # Check if reclassification is needed
            old_value = event_data.get('oldValue', {})
            new_value = event_data.get('value', {})
            
            # Check if description or image was updated
            needs_reclassification = (
                old_value.get('description') != new_value.get('description') or
                old_value.get('image_url') != new_value.get('image_url')
            )
            
            if needs_reclassification:
                logger.info(
                    "Reclassifying updated complaint",
                    complaint_id=complaint_id,
                    description_changed=old_value.get('description') != new_value.get('description'),
                    image_changed=old_value.get('image_url') != new_value.get('image_url')
                )
                
                # Reclassify with new data
                classification = await self.classifier.reclassify_complaint(
                    complaint_id=complaint_id,
                    new_description=new_value.get('description'),
                    force_reclassification=True
                )
                
                # Publish reclassification event
                await self._publish_classification_event(complaint_id, classification, new_value, is_reclassification=True)
                
                return {
                    'success': True,
                    'complaint_id': complaint_id,
                    'reclassified': True,
                    'classification': classification.dict()
                }
            
            return {
                'success': True,
                'complaint_id': complaint_id,
                'reclassified': False,
                'message': 'No reclassification needed'
            }
            
        except Exception as e:
            logger.error(
                "Complaint update trigger failed",
                error=str(e),
                error_type=type(e).__name__,
                event_data=event_data
            )
            raise
    
    async def handle_batch_classification(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle batch classification request
        For processing multiple complaints at once
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            complaint_ids = batch_data.get('complaint_ids', [])
            force_reclassification = batch_data.get('force_reclassification', False)
            
            logger.info(
                "Starting batch classification",
                complaint_count=len(complaint_ids),
                force_reclassification=force_reclassification
            )
            
            # Fetch complaints data
            complaints_data = await self._fetch_complaints_batch(complaint_ids)
            
            # Prepare batch classification data
            batch_classifications = []
            for complaint in complaints_data:
                batch_classifications.append({
                    'id': complaint['id'],
                    'description': complaint.get('description', ''),
                    'image_url': complaint.get('image_url'),
                    'metadata': {
                        'user_id': complaint.get('user_id'),
                        'location': complaint.get('location'),
                        'ward_id': complaint.get('location', {}).get('ward_id'),
                        'batch_classification': True
                    }
                })
            
            # Perform batch classification
            classifications = await self.classifier.batch_classify_complaints(batch_classifications)
            
            # Update all complaints with new classifications
            update_results = []
            for i, classification in enumerate(classifications):
                complaint_id = complaint_ids[i]
                
                # Update complaint
                await self._update_complaint_classification(complaint_id, classification)
                await self._update_complaint_status(complaint_id, ComplaintStatus.CLASSIFIED)
                
                # Publish event
                complaint_data = complaints_data[i]
                await self._publish_classification_event(complaint_id, classification, complaint_data)
                
                update_results.append({
                    'complaint_id': complaint_id,
                    'success': True,
                    'classification': classification.dict()
                })
            
            logger.info(
                "Batch classification completed",
                total_processed=len(complaint_ids),
                successful=len(classifications),
                failed=len(complaint_ids) - len(classifications)
            )
            
            return {
                'success': True,
                'batch_id': batch_data.get('batch_id', f"batch_{datetime.utcnow().timestamp()}"),
                'total_processed': len(complaint_ids),
                'successful': len(classifications),
                'failed': len(complaint_ids) - len(classifications),
                'results': update_results
            }
            
        except Exception as e:
            logger.error(
                "Batch classification failed",
                error=str(e),
                error_type=type(e).__name__,
                batch_data=batch_data
            )
            raise
    
    def _extract_complaint_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complaint data from Firestore event"""
        # Handle different event formats
        if 'value' in event_data:
            # Firestore change event
            return event_data['value'].get('fields', {})
        elif 'data' in event_data:
            # Direct data payload
            return event_data['data']
        else:
            # Direct complaint data
            return event_data
    
    async def _update_complaint_classification(self, complaint_id: str, classification) -> None:
        """Update complaint with classification data"""
        try:
            await self.firestore.collection('complaints').document(complaint_id).update({
                'classification': classification.dict(),
                'classified_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to update complaint classification: {e}")
            raise
    
    async def _update_complaint_status(
        self, 
        complaint_id: str, 
        status: ComplaintStatus,
        error: Optional[str] = None
    ) -> None:
        """Update complaint status"""
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if error:
                update_data['last_error'] = error
                update_data['error_at'] = datetime.utcnow().isoformat()
            
            await self.firestore.collection('complaints').document(complaint_id).update(update_data)
        except Exception as e:
            logger.error(f"Failed to update complaint status: {e}")
            raise
    
    async def _publish_classification_event(
        self,
        complaint_id: str,
        classification,
        complaint_data: Dict[str, Any],
        is_reclassification: bool = False
    ) -> None:
        """Publish classification event for routing"""
        try:
            event_data = {
                'event_type': 'complaint_classified' if not is_reclassification else 'complaint_reclassified',
                'complaint_id': complaint_id,
                'classification': classification.dict(),
                'complaint_data': {
                    'user_id': complaint_data.get('user_id'),
                    'location': complaint_data.get('location'),
                    'ward_id': complaint_data.get('location', {}).get('ward_id'),
                    'created_at': complaint_data.get('created_at')
                },
                'timestamp': datetime.utcnow().isoformat(),
                'requires_routing': True,
                'priority': self._calculate_routing_priority(classification)
            }
            
            # Publish to Pub/Sub
            await publish_event('complaint-classified', event_data)
            
        except Exception as e:
            logger.error(f"Failed to publish classification event: {e}")
            # Don't raise here - classification succeeded, just event publishing failed
    
    def _calculate_routing_priority(self, classification) -> int:
        """Calculate routing priority (1-10, higher = more urgent)"""
        base_priority = 5
        
        # Adjust based on severity
        severity_priority = {
            'critical': 4,
            'high': 3,
            'medium': 1,
            'low': 0
        }
        
        priority = base_priority + severity_priority.get(classification.severity.value, 0)
        
        # Boost for high confidence
        if classification.confidence > 0.9:
            priority += 1
        
        return min(priority, 10)
    
    async def _log_business_event(
        self,
        event_type: str,
        complaint_id: str,
        classification_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> None:
        """Log business event for analytics"""
        try:
            event_doc = {
                'event_type': event_type,
                'complaint_id': complaint_id,
                'classification_data': classification_data,
                'metadata': metadata,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await self.firestore.collection('business_events').add(event_doc)
        except Exception as e:
            logger.error(f"Failed to log business event: {e}")
    
    async def _fetch_complaints_batch(self, complaint_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch multiple complaints from Firestore"""
        try:
            complaints = []
            
            # Fetch in batches to avoid limits
            batch_size = 10
            for i in range(0, len(complaint_ids), batch_size):
                batch_ids = complaint_ids[i:i + batch_size]
                
                # Fetch documents
                docs = await asyncio.gather(*[
                    self.firestore.collection('complaints').document(cid).get()
                    for cid in batch_ids
                ])
                
                for doc in docs:
                    if doc.exists:
                        complaints.append({
                            'id': doc.id,
                            **doc.to_dict()
                        })
            
            return complaints
            
        except Exception as e:
            logger.error(f"Failed to fetch complaints batch: {e}")
            raise


# Global trigger handler instance
_trigger_handler: Optional[ComplaintTriggerHandler] = None


async def get_complaint_trigger_handler() -> ComplaintTriggerHandler:
    """Get or create complaint trigger handler"""
    global _trigger_handler
    
    if not _trigger_handler:
        _trigger_handler = ComplaintTriggerHandler()
        await _trigger_handler.initialize()
    
    return _trigger_handler


# Cloud Function entry points
async def on_complaint_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Cloud Function entry point for complaint creation"""
    handler = await get_complaint_trigger_handler()
    return await handler.handle_complaint_created(event_data)


async def on_complaint_updated(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Cloud Function entry point for complaint update"""
    handler = await get_complaint_trigger_handler()
    return await handler.handle_complaint_updated(event_data)


async def on_batch_classification_request(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Cloud Function entry point for batch classification"""
    handler = await get_complaint_trigger_handler()
    return await handler.handle_batch_classification(event_data)

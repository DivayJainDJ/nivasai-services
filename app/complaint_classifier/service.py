"""
Production-ready Complaint Classifier Service
Handles AI classification of civic complaints with image analysis and structured output
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import base64

from app.shared.gemini.client import get_gemini_client
from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger
from app.shared.schemas.complaint import (
    ComplaintCategory,
    ComplaintSeverity,
    Department,
    ComplaintClassification
)
from app.shared.retry.retry_engine import with_retry, GEMINI_RETRY
from app.shared.validators.complaint_validator import ComplaintValidator

logger = get_logger(__name__)


class ComplaintClassifierService:
    """Production-ready complaint classification service"""
    
    def __init__(self):
        self.gemini = None
        self.firestore = None
        self.validator = ComplaintValidator()
    
    async def initialize(self):
        """Initialize service dependencies"""
        self.gemini = await get_gemini_client()
        self.firestore = await get_firestore_client()
        logger.info("ComplaintClassifierService initialized")
    
    @with_retry(GEMINI_RETRY)
    async def classify_complaint(
        self,
        complaint_id: str,
        description: str,
        image_data: Optional[bytes] = None,
        image_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ComplaintClassification:
        """
        Classify complaint with AI analysis
        
        Args:
            complaint_id: Unique complaint identifier
            description: Text description of complaint
            image_data: Raw image bytes (optional)
            image_url: URL of uploaded image (optional)
            metadata: Additional metadata (location, user info, etc.)
        
        Returns:
            ComplaintClassification with AI-generated analysis
        """
        try:
            logger.info(
                "Starting complaint classification",
                complaint_id=complaint_id,
                has_image=bool(image_data or image_url),
                description_length=len(description)
            )
            
            # Validate input
            validation_result = self.validator.validate_classification_input(
                description=description,
                image_data=image_data,
                image_url=image_url
            )
            
            if not validation_result.is_valid:
                raise ValueError(f"Invalid input: {validation_result.errors}")
            
            # Get image data if URL provided
            if image_url and not image_data:
                image_data = await self._fetch_image_from_url(image_url)
            
            # Perform classification
            classification_result = await self.gemini.classify_complaint(
                description=description,
                image_data=image_data
            )
            
            # Validate and enhance classification
            enhanced_classification = await self._enhance_classification(
                classification_result,
                metadata
            )
            
            # Log classification for analytics
            await self._log_classification_result(
                complaint_id,
                enhanced_classification,
                metadata
            )
            
            logger.info(
                "Complaint classification completed",
                complaint_id=complaint_id,
                category=enhanced_classification.category,
                severity=enhanced_classification.severity,
                confidence=enhanced_classification.confidence
            )
            
            return enhanced_classification
            
        except Exception as e:
            logger.error(
                "Complaint classification failed",
                complaint_id=complaint_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def _fetch_image_from_url(self, image_url: str) -> bytes:
        """Fetch image from URL"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"Failed to fetch image: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Image fetch failed: {e}")
            raise
    
    async def _enhance_classification(
        self,
        classification: Dict[str, Any],
        metadata: Optional[Dict[str, Any]]
    ) -> ComplaintClassification:
        """Enhance classification with business logic and metadata"""
        
        # Map category and severity to enums
        try:
            category = ComplaintCategory(classification.get('category', 'other'))
            severity = ComplaintSeverity(classification.get('severity', 'medium'))
            department = Department(classification.get('suggested_department', 'municipal'))
        except ValueError as e:
            logger.warning(f"Invalid enum value: {e}")
            category = ComplaintCategory.OTHER
            severity = ComplaintSeverity.MEDIUM
            department = Department.MUNICIPAL
        
        # Enhance with location-based logic
        if metadata and 'location' in metadata:
            location = metadata['location']
            # Adjust severity based on location context
            if location.get('is_slum_area', False):
                if severity == ComplaintSeverity.LOW:
                    severity = ComplaintSeverity.MEDIUM
                elif severity == ComplaintSeverity.MEDIUM:
                    severity = ComplaintSeverity.HIGH
        
        # Build enhanced keywords list
        keywords = classification.get('keywords', [])
        if metadata and 'ward_id' in metadata:
            keywords.append(f"ward_{metadata['ward_id']}")
        
        # Create classification object
        enhanced_classification = ComplaintClassification(
            category=category,
            severity=severity,
            confidence=float(classification.get('confidence', 0.7)),
            summary=classification.get('summary', ''),
            suggested_department=department,
            keywords=keywords,
            classified_at=datetime.utcnow()
        )
        
        # Validate confidence threshold
        if enhanced_classification.confidence < 0.6:
            logger.warning(
                "Low confidence classification",
                confidence=enhanced_classification.confidence,
                complaint_id=metadata.get('complaint_id') if metadata else 'unknown'
            )
        
        return enhanced_classification
    
    async def _log_classification_result(
        self,
        complaint_id: str,
        classification: ComplaintClassification,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Log classification result to analytics"""
        try:
            # Log to Firestore analytics collection
            analytics_doc = {
                'complaint_id': complaint_id,
                'category': classification.category.value,
                'severity': classification.severity.value,
                'confidence': classification.confidence,
                'department': classification.suggested_department.value,
                'keywords': classification.keywords,
                'classified_at': classification.classified_at.isoformat(),
                'has_image': bool(metadata and (metadata.get('image_url') or metadata.get('image_data'))),
                'processing_time_ms': metadata.get('processing_time_ms', 0) if metadata else 0
            }
            
            await self.firestore.collection('complaint_analytics').add(analytics_doc)
            
        except Exception as e:
            logger.error(f"Failed to log classification result: {e}")
    
    async def batch_classify_complaints(
        self,
        complaints: List[Dict[str, Any]]
    ) -> List[ComplaintClassification]:
        """
        Classify multiple complaints in batch for efficiency
        
        Args:
            complaints: List of complaint data with description and optional images
            
        Returns:
            List of classification results
        """
        logger.info(f"Starting batch classification for {len(complaints)} complaints")
        
        # Process in parallel with rate limiting
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent classifications
        
        async def classify_single(complaint_data):
            async with semaphore:
                return await self.classify_complaint(
                    complaint_id=complaint_data['id'],
                    description=complaint_data['description'],
                    image_data=complaint_data.get('image_data'),
                    image_url=complaint_data.get('image_url'),
                    metadata=complaint_data.get('metadata')
                )
        
        # Execute all classifications
        results = await asyncio.gather(
            *[classify_single(complaint) for complaint in complaints],
            return_exceptions=True
        )
        
        # Filter out exceptions and log errors
        classifications = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch classification failed for item {i}: {result}")
            else:
                classifications.append(result)
        
        logger.info(f"Batch classification completed: {len(classifications)}/{len(complaints)} successful")
        return classifications
    
    async def get_classification_stats(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get classification statistics for monitoring"""
        try:
            query = self.firestore.collection('complaint_analytics')
            
            if date_from:
                query = query.where('classified_at', '>=', date_from.isoformat())
            if date_to:
                query = query.where('classified_at', '<=', date_to.isoformat())
            
            docs = await query.get()
            
            stats = {
                'total_classifications': len(docs),
                'categories': {},
                'severities': {},
                'departments': {},
                'avg_confidence': 0.0,
                'low_confidence_count': 0
            }
            
            total_confidence = 0.0
            
            for doc in docs:
                data = doc.to_dict()
                
                # Category stats
                category = data.get('category', 'other')
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
                
                # Severity stats
                severity = data.get('severity', 'medium')
                stats['severities'][severity] = stats['severities'].get(severity, 0) + 1
                
                # Department stats
                department = data.get('department', 'municipal')
                stats['departments'][department] = stats['departments'].get(department, 0) + 1
                
                # Confidence stats
                confidence = data.get('confidence', 0.0)
                total_confidence += confidence
                
                if confidence < 0.6:
                    stats['low_confidence_count'] += 1
            
            if stats['total_classifications'] > 0:
                stats['avg_confidence'] = total_confidence / stats['total_classifications']
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get classification stats: {e}")
            raise
    
    async def reclassify_complaint(
        self,
        complaint_id: str,
        new_description: Optional[str] = None,
        new_image_data: Optional[bytes] = None,
        force_reclassification: bool = False
    ) -> ComplaintClassification:
        """
        Reclassify a complaint with new data or forced reclassification
        
        Args:
            complaint_id: Complaint to reclassify
            new_description: Updated description (optional)
            new_image_data: New image data (optional)
            force_reclassification: Force reclassification even if confidence was high
            
        Returns:
            New classification result
        """
        try:
            # Get existing complaint data
            complaint_doc = await self.firestore.collection('complaints').document(complaint_id).get()
            
            if not complaint_doc.exists:
                raise ValueError(f"Complaint {complaint_id} not found")
            
            complaint_data = complaint_doc.to_dict()
            existing_classification = complaint_data.get('classification')
            
            # Check if reclassification is needed
            if (not force_reclassification and 
                existing_classification and 
                existing_classification.get('confidence', 0) >= 0.8):
                logger.info(
                    "Reclassification not needed",
                    complaint_id=complaint_id,
                    existing_confidence=existing_classification.get('confidence')
                )
                return ComplaintClassification(**existing_classification)
            
            # Use new data or existing data
            description = new_description or complaint_data.get('description', '')
            image_data = new_image_data or complaint_data.get('image_data')
            
            # Perform reclassification
            new_classification = await self.classify_complaint(
                complaint_id=complaint_id,
                description=description,
                image_data=image_data,
                metadata={'reclassification': True, 'original_confidence': existing_classification.get('confidence') if existing_classification else None}
            )
            
            # Update complaint with new classification
            await self.firestore.collection('complaints').document(complaint_id).update({
                'classification': new_classification.dict(),
                'reclassified_at': datetime.utcnow().isoformat(),
                'classification_history': complaint_data.get('classification_history', []) + [{
                    'classification': existing_classification,
                    'reclassified_at': datetime.utcnow().isoformat(),
                    'reason': 'user_request' if new_description or new_image_data else 'system_request'
                }]
            })
            
            logger.info(
                "Complaint reclassified successfully",
                complaint_id=complaint_id,
                new_confidence=new_classification.confidence,
                previous_confidence=existing_classification.get('confidence') if existing_classification else None
            )
            
            return new_classification
            
        except Exception as e:
            logger.error(f"Reclassification failed: {e}")
            raise


# Global service instance
_classifier_service: Optional[ComplaintClassifierService] = None


async def get_complaint_classifier() -> ComplaintClassifierService:
    """Get or create complaint classifier service"""
    global _classifier_service
    
    if not _classifier_service:
        _classifier_service = ComplaintClassifierService()
        await _classifier_service.initialize()
    
    return _classifier_service


async def initialize_complaint_classifier():
    """Initialize complaint classifier service"""
    await get_complaint_classifier()

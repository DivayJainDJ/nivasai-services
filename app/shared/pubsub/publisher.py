"""
Pub/Sub publisher for event-driven architecture
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPICallError

from app.config import settings
from app.shared.logging.logger import get_logger
from app.shared.retry.retry_engine import with_retry, DEFAULT_RETRY

logger = get_logger(__name__)


class PubSubPublisher:
    """Pub/Sub event publisher with retry logic"""
    
    def __init__(self):
        self.publisher = None
        self.project_id = settings.FIREBASE_PROJECT_ID
        self._initialized = False
    
    async def initialize(self):
        """Initialize Pub/Sub publisher"""
        try:
            self.publisher = pubsub_v1.PublisherClient()
            self._initialized = True
            logger.info("PubSubPublisher initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PubSubPublisher: {e}")
            raise
    
    @with_retry(DEFAULT_RETRY)
    async def publish_event(
        self,
        topic_name: str,
        event_data: Dict[str, Any],
        attributes: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Publish event to Pub/Sub topic
        
        Args:
            topic_name: Name of the Pub/Sub topic
            event_data: Event payload data
            attributes: Optional message attributes
            
        Returns:
            Message ID
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Prepare topic path
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            
            # Prepare message
            message_data = json.dumps(event_data, default=str).encode('utf-8')
            
            # Prepare attributes
            if attributes is None:
                attributes = {}
            
            # Add default attributes
            attributes.update({
                'event_type': event_data.get('event_type', 'unknown'),
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'nivasai-backend'
            })
            
            # Publish message
            future = self.publisher.publish(
                topic_path,
                data=message_data,
                **attributes
            )
            
            # Get message ID
            message_id = future.result()
            
            logger.info(
                "Event published successfully",
                topic=topic_name,
                message_id=message_id,
                event_type=event_data.get('event_type')
            )
            
            return message_id
            
        except GoogleAPICallError as e:
            logger.error(
                "Pub/Sub API error",
                topic=topic_name,
                error=str(e),
                error_code=e.code if hasattr(e, 'code') else 'unknown'
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to publish event",
                topic=topic_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def publish_complaint_event(
        self,
        event_type: str,
        complaint_id: str,
        data: Dict[str, Any]
    ) -> str:
        """Publish complaint-related event"""
        event_data = {
            'event_type': event_type,
            'complaint_id': complaint_id,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return await self.publish_event('complaint-events', event_data)
    
    async def publish_routing_event(
        self,
        complaint_id: str,
        officer_id: str,
        department: str,
        routing_data: Dict[str, Any]
    ) -> str:
        """Publish complaint routing event"""
        event_data = {
            'event_type': 'complaint_routed',
            'complaint_id': complaint_id,
            'officer_id': officer_id,
            'department': department,
            'routing_data': routing_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        attributes = {
            'complaint_id': complaint_id,
            'officer_id': officer_id,
            'department': department
        }
        
        return await self.publish_event('complaint-routing', event_data, attributes)
    
    async def publish_notification_event(
        self,
        notification_type: str,
        recipient_id: str,
        message: str,
        data: Dict[str, Any]
    ) -> str:
        """Publish notification event"""
        event_data = {
            'event_type': 'send_notification',
            'notification_type': notification_type,
            'recipient_id': recipient_id,
            'message': message,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        attributes = {
            'notification_type': notification_type,
            'recipient_id': recipient_id
        }
        
        return await self.publish_event('notifications', event_data, attributes)
    
    async def publish_analytics_event(
        self,
        event_type: str,
        metrics: Dict[str, Any],
        dimensions: Dict[str, Any]
    ) -> str:
        """Publish analytics event"""
        event_data = {
            'event_type': event_type,
            'metrics': metrics,
            'dimensions': dimensions,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return await self.publish_event('analytics', event_data)
    
    async def publish_housing_event(
        self,
        event_type: str,
        user_id: str,
        housing_data: Dict[str, Any]
    ) -> str:
        """Publish housing-related event"""
        event_data = {
            'event_type': event_type,
            'user_id': user_id,
            'housing_data': housing_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        attributes = {
            'event_type': event_type,
            'user_id': user_id
        }
        
        return await self.publish_event('housing-events', event_data, attributes)
    
    async def publish_ward_analysis_event(
        self,
        ward_id: str,
        analysis_type: str,
        analysis_data: Dict[str, Any]
    ) -> str:
        """Publish ward analysis event"""
        event_data = {
            'event_type': 'ward_analysis',
            'ward_id': ward_id,
            'analysis_type': analysis_type,
            'analysis_data': analysis_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        attributes = {
            'ward_id': ward_id,
            'analysis_type': analysis_type
        }
        
        return await self.publish_event('ward-analysis', event_data, attributes)
    
    async def publish_whatsapp_event(
        self,
        event_type: str,
        phone_number: str,
        message_data: Dict[str, Any]
    ) -> str:
        """Publish WhatsApp-related event"""
        event_data = {
            'event_type': event_type,
            'phone_number': phone_number,
            'message_data': message_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        attributes = {
            'event_type': event_type,
            'phone_number': phone_number
        }
        
        return await self.publish_event('whatsapp-events', event_data, attributes)


# Global publisher instance
_publisher: Optional[PubSubPublisher] = None


async def get_pubsub_publisher() -> PubSubPublisher:
    """Get or create PubSub publisher"""
    global _publisher
    
    if not _publisher:
        _publisher = PubSubPublisher()
        await _publisher.initialize()
    
    return _publisher


async def publish_event(topic_name: str, event_data: Dict[str, Any]) -> str:
    """Convenience function to publish event"""
    publisher = await get_pubsub_publisher()
    return await publisher.publish_event(topic_name, event_data)


async def publish_complaint_event(event_type: str, complaint_id: str, data: Dict[str, Any]) -> str:
    """Convenience function to publish complaint event"""
    publisher = await get_pubsub_publisher()
    return await publisher.publish_complaint_event(event_type, complaint_id, data)


async def publish_routing_event(
    complaint_id: str,
    officer_id: str,
    department: str,
    routing_data: Dict[str, Any]
) -> str:
    """Convenience function to publish routing event"""
    publisher = await get_pubsub_publisher()
    return await publisher.publish_routing_event(complaint_id, officer_id, department, routing_data)


async def publish_notification_event(
    notification_type: str,
    recipient_id: str,
    message: str,
    data: Dict[str, Any]
) -> str:
    """Convenience function to publish notification event"""
    publisher = await get_pubsub_publisher()
    return await publisher.publish_notification_event(notification_type, recipient_id, message, data)

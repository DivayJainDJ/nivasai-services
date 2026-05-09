"""Pub/Sub listener for notification events."""

from __future__ import annotations

import json
import os
from typing import Callable, Optional

from google.cloud import pubsub_v1

from app.notification_broadcaster.schemas import NotificationPayload
from app.notification_broadcaster.service import NotificationBroadcasterService
from app.notification_broadcaster.validator import validate_pubsub_payload
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class PubSubListener:
    """Listener for Pub/Sub notification events."""

    def __init__(self):
        """Initialize Pub/Sub listener."""
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.subscription_name = "notification-events-sub"
        self.topic_name = "notification-events"
        self.service = NotificationBroadcasterService()
        self.subscriber = None
        self.subscription_path = None

    def start(self) -> None:
        """Start listening to Pub/Sub messages."""
        try:
            if not self.project_id:
                logger.error("pubsub_start_failed", reason="missing_project_id")
                return
            
            # Initialize subscriber
            self.subscriber = pubsub_v1.SubscriberClient()
            
            # Build subscription path
            self.subscription_path = self.subscriber.subscription_path(
                self.project_id,
                self.subscription_name,
            )
            
            logger.info(
                "pubsub_listener_starting",
                project=self.project_id,
                subscription=self.subscription_name,
            )
            
            # Start streaming pull
            streaming_pull_future = self.subscriber.subscribe(
                self.subscription_path,
                callback=self._message_callback,
            )
            
            logger.info("pubsub_listener_started", subscription=self.subscription_path)
            
            # Keep listener running
            try:
                streaming_pull_future.result()
            except KeyboardInterrupt:
                logger.info("pubsub_listener_interrupted")
                streaming_pull_future.cancel()
            except Exception as exc:
                logger.error("pubsub_listener_error", error=str(exc))
                streaming_pull_future.cancel()
        
        except Exception as exc:
            logger.error("pubsub_start_failed", error=str(exc))

    def _message_callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        """
        Callback for Pub/Sub messages.
        
        Args:
            message: Pub/Sub message
        """
        try:
            logger.info("pubsub_message_received", message_id=message.message_id)
            
            # Decode message data
            data = message.data.decode("utf-8")
            payload = json.loads(data)
            
            logger.info("message_decoded", payload_type=payload.get("type"))
            
            # Validate payload
            if not validate_pubsub_payload(payload):
                logger.error("invalid_payload", message_id=message.message_id)
                message.ack()  # Acknowledge to prevent redelivery
                return
            
            # Process notification
            notification_payload = NotificationPayload(**payload)
            result = self.service.broadcast_notification(notification_payload)
            
            if result:
                logger.info(
                    "notification_processed",
                    message_id=message.message_id,
                    success=result.get("successCount", 0),
                    failure=result.get("failureCount", 0),
                )
                message.ack()
            else:
                logger.error("notification_processing_failed", message_id=message.message_id)
                # Nack to retry
                message.nack()
        
        except json.JSONDecodeError as exc:
            logger.error("message_decode_failed", error=str(exc), message_id=message.message_id)
            message.ack()  # Don't retry malformed messages
        
        except Exception as exc:
            logger.error("message_callback_failed", error=str(exc), message_id=message.message_id)
            message.nack()  # Retry on unexpected errors

    def stop(self) -> None:
        """Stop listening to Pub/Sub messages."""
        try:
            if self.subscriber and self.subscription_path:
                logger.info("pubsub_listener_stopping")
                # Subscriber will be stopped when streaming_pull_future is cancelled
                logger.info("pubsub_listener_stopped")
        
        except Exception as exc:
            logger.error("pubsub_stop_failed", error=str(exc))

    def publish_notification(self, payload: NotificationPayload) -> bool:
        """
        Publish notification to Pub/Sub topic.
        
        Args:
            payload: Notification payload
        
        Returns:
            True if published successfully, False otherwise
        """
        try:
            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(self.project_id, self.topic_name)
            
            # Convert payload to JSON
            data = payload.model_dump_json().encode("utf-8")
            
            # Publish message
            future = publisher.publish(topic_path, data)
            message_id = future.result()
            
            logger.info("notification_published", message_id=message_id, title=payload.title)
            return True
        
        except Exception as exc:
            logger.error("publish_failed", error=str(exc))
            return False

    def create_subscription_if_not_exists(self) -> bool:
        """
        Create Pub/Sub subscription if it doesn't exist.
        
        Returns:
            True if created or already exists, False on error
        """
        try:
            subscriber = pubsub_v1.SubscriberClient()
            subscription_path = subscriber.subscription_path(
                self.project_id,
                self.subscription_name,
            )
            
            try:
                # Check if subscription exists
                subscriber.get_subscription(request={"subscription": subscription_path})
                logger.info("subscription_exists", subscription=self.subscription_name)
                return True
            
            except Exception:
                # Subscription doesn't exist, create it
                publisher = pubsub_v1.PublisherClient()
                topic_path = publisher.topic_path(self.project_id, self.topic_name)
                
                subscription = subscriber.create_subscription(
                    request={
                        "name": subscription_path,
                        "topic": topic_path,
                        "ack_deadline_seconds": 60,
                    }
                )
                
                logger.info("subscription_created", subscription=subscription.name)
                return True
        
        except Exception as exc:
            logger.error("subscription_creation_failed", error=str(exc))
            return False

    def create_topic_if_not_exists(self) -> bool:
        """
        Create Pub/Sub topic if it doesn't exist.
        
        Returns:
            True if created or already exists, False on error
        """
        try:
            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(self.project_id, self.topic_name)
            
            try:
                # Check if topic exists
                publisher.get_topic(request={"topic": topic_path})
                logger.info("topic_exists", topic=self.topic_name)
                return True
            
            except Exception:
                # Topic doesn't exist, create it
                topic = publisher.create_topic(request={"name": topic_path})
                logger.info("topic_created", topic=topic.name)
                return True
        
        except Exception as exc:
            logger.error("topic_creation_failed", error=str(exc))
            return False

    def setup_pubsub(self) -> bool:
        """
        Set up Pub/Sub topic and subscription.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            logger.info("pubsub_setup_started")
            
            # Create topic
            if not self.create_topic_if_not_exists():
                return False
            
            # Create subscription
            if not self.create_subscription_if_not_exists():
                return False
            
            logger.info("pubsub_setup_completed")
            return True
        
        except Exception as exc:
            logger.error("pubsub_setup_failed", error=str(exc))
            return False


# Global listener instance
_listener_instance: Optional[PubSubListener] = None


def get_pubsub_listener() -> PubSubListener:
    """
    Get global Pub/Sub listener instance.
    
    Returns:
        PubSubListener instance
    """
    global _listener_instance
    if _listener_instance is None:
        _listener_instance = PubSubListener()
    return _listener_instance


def start_pubsub_listener() -> None:
    """Start the global Pub/Sub listener."""
    listener = get_pubsub_listener()
    listener.setup_pubsub()
    listener.start()


def stop_pubsub_listener() -> None:
    """Stop the global Pub/Sub listener."""
    listener = get_pubsub_listener()
    listener.stop()

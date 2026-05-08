"""
WhatsApp chatbot agent service.

Handles WhatsApp user interactions.
"""

from app.shared.logging.logger import get_logger


logger = get_logger(__name__)


class WhatsAppAgentService:
    """Manages WhatsApp chatbot interactions."""

    @staticmethod
    def process_message(sender_id: str, message_text: str) -> str:
        """
        Process incoming WhatsApp message.

        Args:
            sender_id: WhatsApp sender ID
            message_text: Message text

        Returns:
            Response message
        """
        logger.info(
            "Processing WhatsApp message",
            sender_id=sender_id,
            message_length=len(message_text),
        )

        # Placeholder response
        return "Thank you for your message. We've received your complaint and will assist you soon."


def process_message(sender_id: str, message_text: str) -> str:
    """Process WhatsApp message."""
    return WhatsAppAgentService.process_message(sender_id, message_text)

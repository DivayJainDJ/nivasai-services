"""WhatsApp agent package exports."""

from app.whatsapp_agent.service import WhatsAppAgentError, process_whatsapp_message

__all__ = ["process_whatsapp_message", "WhatsAppAgentError"]

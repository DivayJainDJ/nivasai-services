"""Intent classification using Gemini."""

from __future__ import annotations

import json

import google.generativeai as genai

from app.bot_webhook.schemas import IntentClassification
from app.config import settings
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class IntentClassifier:
    """Classify user intent using Gemini."""

    def __init__(self):
        """Initialize intent classifier."""
        self.model = None
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )
            logger.info("intent_classifier_initialized")
        except Exception as exc:
            logger.warning("intent_classifier_init_failed", error=str(exc))

    def classify_intent(
        self,
        message: str,
        has_media: bool = False,
        conversation_history: list[dict] = None,
    ) -> IntentClassification:
        """
        Classify user intent from message.
        
        Args:
            message: User message text
            has_media: Whether message has media attachment
            conversation_history: Previous conversation context
        
        Returns:
            IntentClassification with intent, confidence, language, entities
        """
        if not self.model:
            return self._fallback_classification(message, has_media)
        
        try:
            # Build prompt
            prompt = self._build_classification_prompt(
                message,
                has_media,
                conversation_history,
            )
            
            # Generate classification
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            result = json.loads(response.text)
            
            # Validate and create classification
            classification = IntentClassification(
                intent=result.get("intent", "UNKNOWN"),
                confidence=result.get("confidence", 0.5),
                language=result.get("language", "en"),
                entities=result.get("entities", {}),
            )
            
            logger.info(
                "intent_classified",
                intent=classification.intent,
                confidence=classification.confidence,
                language=classification.language,
            )
            
            return classification
        
        except Exception as exc:
            logger.error("intent_classification_failed", error=str(exc))
            return self._fallback_classification(message, has_media)

    def _build_classification_prompt(
        self,
        message: str,
        has_media: bool,
        conversation_history: list[dict] = None,
    ) -> str:
        """Build classification prompt."""
        context = ""
        if conversation_history:
            recent = conversation_history[-3:]  # Last 3 messages
            context = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in recent
            ])
        
        prompt = f"""Classify the user's intent for a civic services WhatsApp bot.

User Message: "{message}"
Has Media Attachment: {has_media}

Previous Context:
{context if context else "None"}

Supported Intents:
- FILE_COMPLAINT: User wants to file a civic complaint (drainage, roads, sanitation, etc.)
- CHECK_STATUS: User wants to check complaint status (needs complaint ID)
- FIND_HOUSING: User wants to find affordable housing or check eligibility
- DOCUMENT_UPLOAD: User is uploading documents (Aadhaar, income certificate, etc.)
- WARD_INFO: User wants ward information or infrastructure details
- GREET: User is greeting or saying hello
- UNKNOWN: Intent unclear or not supported

Detect Language:
- "en" for English
- "hi" for Hindi

Extract Entities:
- complaint_id: If checking status
- document_type: If uploading document
- ward_id: If asking about ward

Return JSON:
{{
  "intent": "FILE_COMPLAINT",
  "confidence": 0.95,
  "language": "en",
  "entities": {{}}
}}

Classify now:"""
        
        return prompt

    def _fallback_classification(
        self,
        message: str,
        has_media: bool,
    ) -> IntentClassification:
        """Fallback classification without AI."""
        message_lower = message.lower()
        
        # Simple keyword matching
        if any(word in message_lower for word in ["complaint", "problem", "issue", "शिकायत"]):
            intent = "FILE_COMPLAINT"
            confidence = 0.7
        elif any(word in message_lower for word in ["status", "check", "track", "स्थिति"]):
            intent = "CHECK_STATUS"
            confidence = 0.7
        elif any(word in message_lower for word in ["housing", "house", "flat", "आवास"]):
            intent = "FIND_HOUSING"
            confidence = 0.7
        elif has_media or any(word in message_lower for word in ["document", "upload", "दस्तावेज़"]):
            intent = "DOCUMENT_UPLOAD"
            confidence = 0.7
        elif any(word in message_lower for word in ["ward", "area", "वार्ड"]):
            intent = "WARD_INFO"
            confidence = 0.7
        elif any(word in message_lower for word in ["hello", "hi", "hey", "नमस्ते", "हेलो"]):
            intent = "GREET"
            confidence = 0.8
        else:
            intent = "UNKNOWN"
            confidence = 0.5
        
        # Detect language
        language = "hi" if any(c in message for c in "अआइईउऊएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह") else "en"
        
        return IntentClassification(
            intent=intent,
            confidence=confidence,
            language=language,
            entities={},
        )

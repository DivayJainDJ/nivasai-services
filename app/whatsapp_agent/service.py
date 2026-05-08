"""
Production-ready WhatsApp Agent Service
Handles WhatsApp interactions, intent classification, and conversation management
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import re

from app.shared.firestore.client import get_firestore_client
from app.shared.gemini.client import get_gemini_client
from app.shared.logging.logger import get_logger
from app.shared.retry.retry_engine import with_retry, DEFAULT_RETRY
from app.shared.schemas.whatsapp import (
    WhatsAppMessage, ConversationState, IntentType, 
    MessageDirection, ConversationContext
)
from app.shared.validators.whatsapp_validator import WhatsAppValidator
from app.shared.notifications.twilio_client import get_twilio_client

logger = get_logger(__name__)


class WhatsAppAgentService:
    """Production-ready WhatsApp agent service"""
    
    def __init__(self):
        self.firestore = None
        self.gemini = None
        self.twilio = None
        self.validator = WhatsAppValidator()
        self._initialized = False
        
        # Conversation state management
        self.conversation_cache = {}
        self.session_timeout_minutes = 30
    
    async def initialize(self):
        """Initialize WhatsApp agent dependencies"""
        self.firestore = await get_firestore_client()
        self.gemini = await get_gemini_client()
        self.twilio = await get_twilio_client()
        self._initialized = True
        logger.info("WhatsAppAgentService initialized")
    
    @with_retry(DEFAULT_RETRY)
    async def process_incoming_message(
        self,
        from_number: str,
        message_body: str,
        media_url: Optional[str] = None,
        message_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Process incoming WhatsApp message
        
        Args:
            from_number: Sender's phone number
            message_body: Message text content
            media_url: Optional media attachment URL
            message_timestamp: Message timestamp
            
        Returns:
            Processing result with response
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            logger.info(
                "Processing incoming WhatsApp message",
                from_number=from_number,
                message_length=len(message_body),
                has_media=bool(media_url)
            )
            
            # Validate message
            validation_result = self.validator.validate_incoming_message(
                from_number, message_body, media_url
            )
            if not validation_result.is_valid:
                return {
                    'success': False,
                    'error': 'Invalid message',
                    'details': validation_result.errors
                }
            
            # Get or create conversation context
            conversation = await self._get_or_create_conversation(from_number)
            
            # Create message object
            message = WhatsAppMessage(
                from_number=from_number,
                message_body=message_body,
                media_url=media_url,
                direction=MessageDirection.INCOMING,
                timestamp=message_timestamp or datetime.utcnow(),
                message_id=self._generate_message_id()
            )
            
            # Detect intent
            intent = await self._detect_message_intent(message, conversation)
            
            # Process based on intent
            response = await self._process_intent(intent, message, conversation)
            
            # Update conversation context
            await self._update_conversation_context(conversation, message, intent, response)
            
            # Send response via WhatsApp
            if response.get('should_reply', True):
                await self._send_whatsapp_response(
                    from_number,
                    response.get('response_text', ''),
                    response.get('media_urls', [])
                )
            
            # Log conversation event
            await self._log_conversation_event(message, intent, response)
            
            logger.info(
                "WhatsApp message processed",
                from_number=from_number,
                intent=intent.intent_type,
                response_sent=response.get('should_reply', True)
            )
            
            return {
                'success': True,
                'intent': intent.dict(),
                'response': response,
                'conversation_id': conversation.conversation_id
            }
            
        except Exception as e:
            logger.error(
                "WhatsApp message processing failed",
                from_number=from_number,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Send error message
            await self._send_error_message(from_number)
            
            raise
    
    async def _get_or_create_conversation(self, phone_number: str) -> ConversationContext:
        """Get existing conversation or create new one"""
        try:
            # Check cache first
            if phone_number in self.conversation_cache:
                cached_conversation = self.conversation_cache[phone_number]
                
                # Check if still valid
                if datetime.utcnow() - cached_conversation.last_activity < timedelta(minutes=self.session_timeout_minutes):
                    return cached_conversation
            
            # Query Firestore for existing conversation
            conversation_query = self.firestore.collection('whatsapp_conversations').where(
                'phone_number', '==', phone_number
            ).where('status', '==', 'active').get()
            
            if conversation_query.docs:
                # Load existing conversation
                conversation_data = conversation_query.docs[0].to_dict()
                conversation = ConversationContext(**conversation_data)
                
                # Check if conversation expired
                if datetime.utcnow() - conversation.last_activity > timedelta(hours=24):
                    # Reset conversation state
                    conversation.state = ConversationState.GREETING
                    conversation.context = {}
            else:
                # Create new conversation
                conversation = ConversationContext(
                    conversation_id=self._generate_conversation_id(),
                    phone_number=phone_number,
                    state=ConversationState.GREETING,
                    started_at=datetime.utcnow(),
                    last_activity=datetime.utcnow()
                )
                
                # Save to Firestore
                await self.firestore.collection('whatsapp_conversations').document(
                    conversation.conversation_id
                ).set(conversation.dict())
            
            # Update cache
            self.conversation_cache[phone_number] = conversation
            
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to get/create conversation: {e}")
            # Return default conversation
            return ConversationContext(
                conversation_id=self._generate_conversation_id(),
                phone_number=phone_number,
                state=ConversationState.GREETING,
                started_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
    
    async def _detect_message_intent(
        self,
        message: WhatsAppMessage,
        conversation: ConversationContext
    ) -> Dict[str, Any]:
        """Detect intent from message using AI"""
        try:
            # Get conversation history for context
            history = await self._get_conversation_history(conversation.conversation_id, limit=5)
            
            # Use Gemini to detect intent
            intent_result = await self.gemini.detect_whatsapp_intent(
                message_body=message.message_body,
                conversation_history=history
            )
            
            # Enhance with rule-based detection
            enhanced_intent = self._enhance_intent_with_rules(intent_result, message, conversation)
            
            return enhanced_intent
            
        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            # Return default intent
            return {
                'intent_type': IntentType.UNKNOWN,
                'confidence': 0.1,
                'entities': {},
                'response_suggestion': 'I did not understand. Could you please rephrase?'
            }
    
    def _enhance_intent_with_rules(
        self,
        ai_intent: Dict[str, Any],
        message: WhatsAppMessage,
        conversation: ConversationContext
    ) -> Dict[str, Any]:
        """Enhance AI intent with rule-based detection"""
        text = message.message_body.lower()
        
        # Rule-based patterns
        patterns = {
            IntentType.COMPLAINT_REGISTER: [
                r'complaint', r'problem', r'issue', r'broken', r'leak', r'damage',
                r'शिकायत', r'समस्या', r'टूटा', r'खराब'
            ],
            IntentType.COMPLAINT_STATUS: [
                r'status', r'update', r'progress', r'what happened',
                r'स्थिति', r'अपडेट', r'क्या हुआ'
            ],
            IntentType.HOUSING_QUERY: [
                r'house', r'flat', r'housing', r'pmay', r'scheme',
                r'घर', r'मकान', r'आवास', r'योजना'
            ],
            IntentType.WARD_INFO: [
                r'ward', r'area', r'location', r'my ward',
                r'वार्ड', r'क्षेत्र', r'इलाका'
            ],
            IntentType.HELP: [
                r'help', r'support', r'assist', r'how to',
                r'मदद', r'सहायता', r'कैसे'
            ],
            IntentType.GREETING: [
                r'hello', r'hi', r'namaste', r'good morning',
                r'नमस्ते', r'हेलो', r'सुप्रभात'
            ]
        }
        
        # Check patterns
        for intent_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text):
                    return {
                        'intent_type': intent_type,
                        'confidence': 0.9,
                        'entities': ai_intent.get('entities', {}),
                        'response_suggestion': ai_intent.get('response_suggestion', ''),
                        'detection_method': 'rule_based'
                    }
        
        # Return AI intent if no rule matched
        return ai_intent
    
    async def _process_intent(
        self,
        intent: Dict[str, Any],
        message: WhatsAppMessage,
        conversation: ConversationContext
    ) -> Dict[str, Any]:
        """Process detected intent and generate response"""
        try:
            intent_type = intent.get('intent_type', IntentType.UNKNOWN)
            
            # Route to appropriate handler
            if intent_type == IntentType.COMPLAINT_REGISTER:
                return await self._handle_complaint_registration(message, conversation, intent)
            elif intent_type == IntentType.COMPLAINT_STATUS:
                return await self._handle_complaint_status(message, conversation, intent)
            elif intent_type == IntentType.HOUSING_QUERY:
                return await self._handle_housing_query(message, conversation, intent)
            elif intent_type == IntentType.WARD_INFO:
                return await self._handle_ward_info(message, conversation, intent)
            elif intent_type == IntentType.HELP:
                return await self._handle_help_request(message, conversation, intent)
            elif intent_type == IntentType.GREETING:
                return await self._handle_greeting(message, conversation, intent)
            else:
                return await self._handle_unknown_intent(message, conversation, intent)
                
        except Exception as e:
            logger.error(f"Intent processing failed: {e}")
            return {
                'response_text': 'I apologize, but I encountered an error. Please try again.',
                'should_reply': True,
                'intent_processed': False
            }
    
    async def _handle_complaint_registration(
        self,
        message: WhatsAppMessage,
        conversation: ConversationContext,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle complaint registration intent"""
        try:
            # Extract entities from intent
            entities = intent.get('entities', {})
            complaint_type = entities.get('complaint_type')
            description = message.message_body
            
            # Check if we have enough information
            if not complaint_type:
                return {
                    'response_text': 'I can help you register a complaint. What type of issue are you facing? (e.g., water, drainage, roads, electricity)',
                    'should_reply': True,
                    'next_state': ConversationState.AWAITING_COMPLAINT_TYPE,
                    'intent_processed': True
                }
            
            # Check if location is provided
            if not conversation.context.get('location'):
                return {
                    'response_text': 'Please share your location or ward number so I can register your complaint.',
                    'should_reply': True,
                    'next_state': ConversationState.AWAITING_LOCATION,
                    'intent_processed': True
                }
            
            # Create complaint
            complaint_data = {
                'user_phone': message.from_number,
                'complaint_type': complaint_type,
                'description': description,
                'location': conversation.context.get('location'),
                'source': 'whatsapp',
                'media_url': message.media_url,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Save complaint to Firestore
            complaint_ref = await self.firestore.collection('complaints').add(complaint_data)
            complaint_id = complaint_ref.id
            
            response_text = f"""
✅ Your complaint has been registered successfully!

Complaint ID: {complaint_id}
Type: {complaint_type}
Status: Under Review

We will process your complaint and update you on the progress. You can check status anytime by sending: "status {complaint_id}"
            """.strip()
            
            return {
                'response_text': response_text,
                'should_reply': True,
                'complaint_id': complaint_id,
                'next_state': ConversationState.CONFIRMATION,
                'intent_processed': True
            }
            
        except Exception as e:
            logger.error(f"Complaint registration failed: {e}")
            return {
                'response_text': 'I apologize, but I could not register your complaint. Please try again later.',
                'should_reply': True,
                'intent_processed': False
            }
    
    async def _handle_complaint_status(
        self,
        message: WhatsAppMessage,
        conversation: ConversationContext,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle complaint status inquiry"""
        try:
            entities = intent.get('entities', {})
            complaint_id = entities.get('complaint_id')
            
            if not complaint_id:
                # Try to extract complaint ID from message
                id_pattern = r'(?:status|update)\s+([A-Z0-9]{8,})'
                match = re.search(id_pattern, message.message_body, re.IGNORECASE)
                if match:
                    complaint_id = match.group(1)
            
            if not complaint_id:
                return {
                    'response_text': 'Please provide your complaint ID to check status. You can find it in the confirmation message.',
                    'should_reply': True,
                    'intent_processed': True
                }
            
            # Get complaint from Firestore
            complaint_doc = await self.firestore.collection('complaints').document(complaint_id).get()
            
            if not complaint_doc.exists:
                return {
                    'response_text': f'Complaint {complaint_id} not found. Please check the ID and try again.',
                    'should_reply': True,
                    'intent_processed': True
                }
            
            complaint = complaint_doc.to_dict()
            
            # Format status response
            status_emoji = {
                'pending': '⏳',
                'classified': '🔍',
                'routed': '📋',
                'in_progress': '🔧',
                'resolved': '✅',
                'escalated': '🚨'
            }
            
            emoji = status_emoji.get(complaint.get('status', 'pending'), '📋')
            
            response_text = f"""
{emoji} Complaint Status

ID: {complaint_id}
Type: {complaint.get('complaint_type', 'Unknown')}
Status: {complaint.get('status', 'Unknown').title()}
Created: {complaint.get('created_at', 'Unknown')}

"""
            
            if complaint.get('assigned_officer'):
                response_text += f"Assigned Officer: {complaint['assigned_officer']}\n"
            
            if complaint.get('estimated_resolution'):
                response_text += f"Estimated Resolution: {complaint['estimated_resolution']}\n"
            
            response_text += "\nReply 'details' for more information or 'help' for assistance."
            
            return {
                'response_text': response_text.strip(),
                'should_reply': True,
                'intent_processed': True
            }
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {
                'response_text': 'I could not retrieve the complaint status. Please try again later.',
                'should_reply': True,
                'intent_processed': False
            }
    
    async def _handle_housing_query(
        self,
        message: WhatsAppMessage,
        conversation: ConversationContext,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle housing-related queries"""
        try:
            entities = intent.get('entities', {})
            query_type = entities.get('query_type', 'general')
            
            if query_type == 'eligibility':
                return {
                    'response_text': '''
🏠 Housing Eligibility Information

PMAY-U schemes are available for:
• EWS: Annual income up to ₹3 Lakhs
• LIG: Annual income up to ₹6 Lakhs  
• MIG1: Annual income up to ₹12 Lakhs
• MIG2: Annual income up to ₹18 Lakhs

Required documents:
• Aadhaar card, PAN card
• Income certificate
• Residence proof

Reply "apply" to start your housing application or "check" to check eligibility.
                    '''.strip(),
                    'should_reply': True,
                    'intent_processed': True
                }
            
            elif query_type == 'application':
                return {
                    'response_text': '''
📋 Housing Application Process

To apply for housing:
1. Check your eligibility (reply "check eligibility")
2. Gather required documents
3. Visit housing authority office
4. Submit application form
5. Wait for verification (2-4 weeks)

Reply "documents" for complete document list or "office" for office locations.
                    '''.strip(),
                    'should_reply': True,
                    'intent_processed': True
                }
            
            else:
                return {
                    'response_text': '''
🏠 I can help you with housing information!

Available services:
• Check eligibility (reply "check eligibility")
• Application process (reply "apply")
• Document requirements (reply "documents")
• Office locations (reply "office")

What would you like to know?
                    '''.strip(),
                    'should_reply': True,
                    'intent_processed': True
                }
                
        except Exception as e:
            logger.error(f"Housing query failed: {e})
            return {
                'response_text': 'I could not process your housing query. Please try again.',
                'should_reply': True,
                'intent_processed': False
            }
    
    async def _handle_ward_info(
        self,
        message: WhatsAppMessage,
        conversation: ConversationContext,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle ward information requests"""
        try:
            entities = intent.get('entities', {})
            ward_id = entities.get('ward_id')
            
            if not ward_id:
                return {
                    'response_text': 'Please provide your ward number to get information about your area.',
                    'should_reply': True,
                    'intent_processed': True
                }
            
            # Get ward information from Firestore
            ward_doc = await self.firestore.collection('wards').document(ward_id).get()
            
            if not ward_doc.exists:
                return {
                    'response_text': f'Ward {ward_id} information not available. Please check the ward number.',
                    'should_reply': True,
                    'intent_processed': True
                }
            
            ward = ward_doc.to_dict()
            
            response_text = f"""
📍 Ward {ward_id} Information

Name: {ward.get('name', 'Unknown')}
Councillor: {ward.get('councillor_name', 'Not assigned')}
Office: {ward.get('office_number', 'Not available')}

Services in your ward:
• Water supply: {ward.get('water_office', 'Contact main office')}
• Electricity: {ward.get('electricity_office', 'Contact main office')}
• Sanitation: {ward.get('sanitation_office', 'Contact main office')}

Reply "complaint" to report issues in your ward.
            """.strip()
            
            return {
                'response_text': response_text,
                'should_reply': True,
                'intent_processed': True
            }
            
        except Exception as e:
            logger.error(f"Ward info failed: {e}")
            return {
                'response_text': 'I could not retrieve ward information. Please try again.',
                'should_reply': True,
                'intent_processed': False
            }
    
    async def _handle_help_request(
        self,
        message: WhatsAppMessage,
        conversation: ConversationContext,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle help requests"""
        help_text = '''
🤖 NivasAI WhatsApp Help

I can help you with:

📝 Complaints
• Register new complaints
• Check complaint status
• Get updates on progress

🏠 Housing Services  
• Check eligibility
• Application process
• Document requirements

📍 Ward Information
• Get ward details
• Contact information
• Services available

💬 Commands
• "complaint" - Register issue
• "status <ID>" - Check status
• "housing" - Housing help
• "ward <number>" - Ward info
• "help" - This message

Reply with any keyword to get started!
        '''.strip()
        
        return {
            'response_text': help_text,
            'should_reply': True,
            'intent_processed': True
        }
    
    async def _handle_greeting(
        self,
        message: WhatsAppMessage,
        conversation: ConversationContext,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle greeting messages"""
        greeting_responses = [
            "👋 Hello! Welcome to NivasAI. How can I help you today?",
            "🙏 Namaste! I'm here to assist you. What do you need help with?",
            "😊 Good day! I'm your civic assistant. How can I help?",
            "🤝 Welcome! I can help with complaints, housing, and ward information."
        ]
        
        import random
        response = random.choice(greeting_responses)
        
        return {
            'response_text': response,
            'should_reply': True,
            'intent_processed': True
        }
    
    async def _handle_unknown_intent(
        self,
        message: WhatsAppMessage,
        conversation: ConversationContext,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle unknown or unclear intents"""
        return {
            'response_text': 'I did not understand that. You can say "help" to see what I can do, or try describing your issue.',
            'should_reply': True,
            'intent_processed': True
        }
    
    async def _send_whatsapp_response(
        self,
        to_number: str,
        message_text: str,
        media_urls: Optional[List[str]] = None
    ) -> None:
        """Send response via WhatsApp"""
        try:
            if media_urls:
                # Send media message
                await self.twilio.send_media_message(to_number, message_text, media_urls)
            else:
                # Send text message
                await self.twilio.send_text_message(to_number, message_text)
                
        except Exception as e:
            logger.error(f"Failed to send WhatsApp response: {e}")
    
    async def _send_error_message(self, to_number: str) -> None:
        """Send error message to user"""
        error_message = "I apologize, but I'm having trouble processing your request. Please try again later."
        try:
            await self.twilio.send_text_message(to_number, error_message)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    async def _update_conversation_context(
        self,
        conversation: ConversationContext,
        message: WhatsAppMessage,
        intent: Dict[str, Any],
        response: Dict[str, Any]
    ) -> None:
        """Update conversation context"""
        try:
            # Update conversation
            conversation.last_activity = datetime.utcnow()
            conversation.message_count += 1
            
            # Update state if provided
            if response.get('next_state'):
                conversation.state = response['next_state']
            
            # Update context with extracted entities
            if intent.get('entities'):
                conversation.context.update(intent['entities'])
            
            # Save to Firestore
            await self.firestore.collection('whatsapp_conversations').document(
                conversation.conversation_id
            ).update({
                'last_activity': conversation.last_activity.isoformat(),
                'message_count': conversation.message_count,
                'state': conversation.state.value,
                'context': conversation.context
            })
            
            # Update cache
            self.conversation_cache[message.from_number] = conversation
            
        except Exception as e:
            logger.error(f"Failed to update conversation context: {e}")
    
    async def _get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get conversation history for context"""
        try:
            messages_query = self.firestore.collection('whatsapp_messages').where(
                'conversation_id', '==', conversation_id
            ).order_by('timestamp', direction='DESC').limit(limit).get()
            
            history = []
            for doc in messages_query.docs:
                message_data = doc.to_dict()
                history.append({
                    'message': message_data.get('message_body', ''),
                    'direction': message_data.get('direction', 'unknown'),
                    'timestamp': message_data.get('timestamp')
                })
            
            return list(reversed(history))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def _log_conversation_event(
        self,
        message: WhatsAppMessage,
        intent: Dict[str, Any],
        response: Dict[str, Any]
    ) -> None:
        """Log conversation event for analytics"""
        try:
            event_data = {
                'conversation_id': message.from_number,  # Use phone number as ID for simplicity
                'message_id': message.message_id,
                'message_body': message.message_body,
                'direction': message.direction.value,
                'intent_type': intent.get('intent_type', 'unknown').value,
                'intent_confidence': intent.get('confidence', 0.0),
                'response_sent': response.get('should_reply', False),
                'timestamp': message.timestamp.isoformat()
            }
            
            await self.firestore.collection('whatsapp_events').add(event_data)
            
        except Exception as e:
            logger.error(f"Failed to log conversation event: {e}")
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _generate_conversation_id(self) -> str:
        """Generate unique conversation ID"""
        import uuid
        return str(uuid.uuid4())
    
    async def get_conversation_analytics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get conversation analytics"""
        try:
            query = self.firestore.collection('whatsapp_events')
            
            if date_from:
                query = query.where('timestamp', '>=', date_from.isoformat())
            if date_to:
                query = query.where('timestamp', '<=', date_to.isoformat())
            
            docs = await query.get()
            
            analytics = {
                'total_messages': len(docs),
                'incoming_messages': 0,
                'outgoing_messages': 0,
                'intents': {},
                'avg_confidence': 0.0,
                'response_rate': 0.0
            }
            
            total_confidence = 0.0
            responses_sent = 0
            
            for doc in docs:
                data = doc.to_dict()
                
                # Count directions
                if data.get('direction') == 'incoming':
                    analytics['incoming_messages'] += 1
                else:
                    analytics['outgoing_messages'] += 1
                
                # Count intents
                intent = data.get('intent_type', 'unknown')
                analytics['intents'][intent] = analytics['intents'].get(intent, 0) + 1
                
                # Confidence
                confidence = data.get('intent_confidence', 0.0)
                total_confidence += confidence
                
                # Response rate
                if data.get('response_sent', False):
                    responses_sent += 1
            
            if analytics['total_messages'] > 0:
                analytics['avg_confidence'] = total_confidence / analytics['total_messages']
                analytics['response_rate'] = responses_sent / analytics['incoming_messages']
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get conversation analytics: {e}")
            return {}


# Global service instance
_whatsapp_agent: Optional[WhatsAppAgentService] = None


async def get_whatsapp_agent() -> WhatsAppAgentService:
    """Get or create WhatsApp agent service"""
    global _whatsapp_agent
    
    if not _whatsapp_agent:
        _whatsapp_agent = WhatsAppAgentService()
        await _whatsapp_agent.initialize()
    
    return _whatsapp_agent


async def initialize_whatsapp_agent():
    """Initialize WhatsApp agent service"""
    await get_whatsapp_agent()

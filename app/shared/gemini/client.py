"""
Google Gemini AI Client
Handles all interactions with Google Gemini API
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
import aiohttp
from google.generativeai import GenerativeModel, configure
import google.generativeai as genai

from app.config import settings
from app.shared.logging.logger import get_logger
from app.shared.retry.retry_engine import with_retry, RetryConfig

logger = get_logger(__name__)


class GeminiClient:
    """Google Gemini AI client wrapper"""
    
    def __init__(self):
        self._model = None
        self._vision_model = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Gemini client"""
        try:
            configure(api_key=settings.GEMINI_API_KEY)
            
            # Text model
            self._model = GenerativeModel("gemini-1.5-pro")
            
            # Vision model
            self._vision_model = GenerativeModel("gemini-1.5-pro-vision")
            
            self._initialized = True
            logger.info("Gemini client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    @property
    def model(self) -> GenerativeModel:
        """Get text model"""
        if not self._initialized:
            raise RuntimeError("Gemini client not initialized")
        return self._model
    
    @property
    def vision_model(self) -> GenerativeModel:
        """Get vision model"""
        if not self._initialized:
            raise RuntimeError("Gemini client not initialized")
        return self._vision_model
    
    @with_retry(RetryConfig(max_retries=3, base_delay=1.0))
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate text response"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Text generation error: {e}")
            raise
    
    @with_retry(RetryConfig(max_retries=3, base_delay=1.0))
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Analyze image with vision model"""
        try:
            import PIL.Image
            from io import BytesIO
            
            # Convert bytes to PIL Image
            image = PIL.Image.open(BytesIO(image_data))
            
            response = await asyncio.to_thread(
                self.vision_model.generate_content,
                [prompt, image],
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": 1000,
                }
            )
            
            return {
                "analysis": response.text,
                "image_info": {
                    "size": image.size,
                    "mode": image.mode,
                    "format": image.format
                }
            }
            
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            raise
    
    @with_retry(RetryConfig(max_retries=3, base_delay=1.0))
    async def generate_structured_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured JSON response"""
        try:
            # Add schema instruction to prompt
            schema_instruction = f"""
            Please respond with a valid JSON object that follows this schema:
            {json.dumps(schema, indent=2)}
            
            Your response should be ONLY the JSON object, nothing else.
            """
            
            full_prompt = f"{prompt}\n\n{schema_instruction}"
            
            response = await self.generate_text(
                full_prompt,
                temperature=temperature,
                max_tokens=2000
            )
            
            # Parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise ValueError("Could not extract JSON from response")
                    
        except Exception as e:
            logger.error(f"Structured response generation error: {e}")
            raise
    
    async def classify_complaint(
        self,
        description: str,
        image_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Classify complaint category and severity"""
        try:
            from app.shared.prompts.complaint_classifier import get_classification_prompt
            
            prompt = get_classification_prompt(description)
            
            schema = {
                "category": "string",
                "severity": "string",
                "confidence": "number",
                "summary": "string",
                "suggested_department": "string",
                "keywords": ["string"]
            }
            
            if image_data:
                # Use vision model for image + text
                vision_prompt = f"""
                Analyze this complaint image and description:
                Description: {description}
                
                Classify the complaint based on both the image and description.
                """
                
                vision_response = await self.analyze_image(image_data, vision_prompt)
                
                # Combine vision analysis with text classification
                combined_prompt = f"""
                Based on this image analysis and description:
                Image Analysis: {vision_response['analysis']}
                Description: {description}
                
                Provide a final classification following this schema:
                {json.dumps(schema, indent=2)}
                """
                
                return await self.generate_structured_response(
                    combined_prompt,
                    schema
                )
            else:
                # Text-only classification
                return await self.generate_structured_response(prompt, schema)
                
        except Exception as e:
            logger.error(f"Complaint classification error: {e}")
            raise
    
    async def analyze_ward_infrastructure(
        self,
        ward_id: str,
        ward_name: str,
        coordinates: Dict[str, float],
        satellite_image: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Analyze ward infrastructure"""
        try:
            from app.shared.prompts.ward_analyzer import get_ward_analysis_prompt
            
            prompt = get_ward_analysis_prompt(ward_id, ward_name, coordinates)
            
            schema = {
                "scores": {
                    "road_connectivity": "number",
                    "water_access": "number",
                    "sanitation_coverage": "number",
                    "electricity_access": "number",
                    "green_coverage": "number",
                    "informal_settlements": "number"
                },
                "summary": "string",
                "top_priority": "string",
                "estimated_population": "number",
                "recommendations": ["string"]
            }
            
            if satellite_image:
                # Analyze satellite image
                vision_prompt = f"""
                Analyze this satellite image of Ward {ward_name} ({ward_id}).
                Focus on infrastructure: roads, water systems, sanitation, electricity, green spaces.
                """
                
                vision_response = await self.analyze_image(satellite_image, vision_prompt)
                
                # Combine with structured analysis
                combined_prompt = f"""
                Satellite Image Analysis: {vision_response['analysis']}
                
                Ward Information:
                - Ward ID: {ward_id}
                - Name: {ward_name}
                - Coordinates: {coordinates}
                
                Provide a comprehensive infrastructure analysis following this schema:
                {json.dumps(schema, indent=2)}
                """
                
                return await self.generate_structured_response(
                    combined_prompt,
                    schema
                )
            else:
                return await self.generate_structured_response(prompt, schema)
                
        except Exception as e:
            logger.error(f"Ward analysis error: {e}")
            raise
    
    async def match_housing_eligibility(
        self,
        family_profile: Dict[str, Any],
        available_units: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Match housing eligibility and rank units"""
        try:
            from app.shared.prompts.housing_matcher import get_housing_matching_prompt
            
            prompt = get_housing_matching_prompt(family_profile, available_units)
            
            schema = {
                "matches": [
                    {
                        "unit_id": "string",
                        "score": "number",
                        "explanation": "string",
                        "eligible": "boolean",
                        "missing_documents": ["string"],
                        "priority_rank": "number"
                    }
                ]
            }
            
            response = await self.generate_structured_response(prompt, schema)
            return response.get("matches", [])
            
        except Exception as e:
            logger.error(f"Housing matching error: {e}")
            raise
    
    async def detect_whatsapp_intent(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Detect WhatsApp message intent"""
        try:
            from app.shared.prompts.whatsapp_intent import get_intent_detection_prompt
            
            prompt = get_intent_detection_prompt(message, conversation_history)
            
            schema = {
                "intent": "string",
                "confidence": "number",
                "entities": {
                    "complaint_type": "string",
                    "phone_number": "string",
                    "complaint_id": "string",
                    "income_amount": "number",
                    "family_size": "number"
                },
                "response_suggestion": "string"
            }
            
            return await self.generate_structured_response(prompt, schema)
            
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            raise


# Global client instance
_gemini_client: Optional[GeminiClient] = None


async def get_gemini_client() -> GeminiClient:
    """Get or create Gemini client"""
    global _gemini_client
    
    if not _gemini_client:
        _gemini_client = GeminiClient()
        await _gemini_client.initialize()
    
    return _gemini_client


async def initialize_gemini():
    """Initialize Gemini client"""
    await get_gemini_client()

"""
Core complaint classification logic with AI integration
"""

import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from app.shared.schemas.complaint import (
    ComplaintCategory,
    ComplaintSeverity,
    Department
)
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ClassificationFeatures:
    """Features extracted for classification"""
    keywords: List[str]
    urgency_indicators: List[str]
    location_context: Dict[str, Any]
    severity_indicators: List[str]
    category_indicators: Dict[str, int]


class ComplaintClassifier:
    """Core classification logic engine"""
    
    def __init__(self):
        self.category_keywords = self._load_category_keywords()
        self.severity_keywords = self._load_severity_keywords()
        self.department_mapping = self._load_department_mapping()
    
    def _load_category_keywords(self) -> Dict[str, List[str]]:
        """Load keyword mappings for categories"""
        return {
            'water': [
                'water', 'paani', 'jal', 'tank', 'tap', 'supply', 'leak', 'pipe',
                'bohar', 'pani', 'nalka', 'tanker', 'connection', 'pipeline',
                'जल', 'पानी', 'पाइप', 'टैंक', 'लीक', 'बोरवेल'
            ],
            'sanitation': [
                'drain', 'sewer', 'toilet', 'garbage', 'waste', 'cleanliness',
                'naali', 'safai', 'kachra', 'gutter', 'sewage', 'trash',
                'ड्रेन', 'सीवर', 'शौचालय', 'कचरा', 'गटर', 'सफाई'
            ],
            'roads': [
                'road', 'street', 'pothole', 'traffic', 'footpath', 'bridge',
                'sadak', 'rasta', 'gadda', 'chauraha', 'path', 'highway',
                'सड़क', 'रास्ता', 'गड्ढा', 'चौराहा', 'पथ', 'पुल'
            ],
            'electricity': [
                'electricity', 'power', 'light', 'streetlight', 'connection',
                'bijli', 'light', 'pole', 'wire', 'transformer', 'outage',
                'बिजली', 'बिजली', 'खंब', 'पोल', 'तार', 'ट्रांसफॉर्मर'
            ],
            'housing': [
                'house', 'flat', 'building', 'construction', 'repair', 'leak',
                'ghar', 'makaan', 'building', 'wall', 'roof', 'foundation',
                'घर', 'मकान', 'दीवार', 'छत', 'दीवार', 'नींव'
            ],
            'waste': [
                'garbage', 'trash', 'dump', 'collection', 'bin', 'disposal',
                'kachra', 'kachra', 'dumping', 'landfill', 'recycling',
                'कचरा', 'गटर', 'डंप', 'बिन', 'रिसाइकलिंग'
            ],
            'street_lights': [
                'streetlight', 'light', 'pole', 'dark', 'illumination',
                'street light', 'lamp', 'bulb', 'led', 'road light',
                'स्ट्रीट लाइट', 'बत्ती', 'पोल', 'अंधेरा', 'रोशनी'
            ],
            'drainage': [
                'drain', 'drainage', 'waterlogging', 'flood', 'rain',
                'naali', 'pani bharna', 'jal bharna', 'overflow',
                'नाली', 'जल भरना', 'बाढ़', 'ओवरफ्लो'
            ],
            'eviction': [
                'eviction', 'remove', 'demolish', 'illegal', 'encroachment',
                'utaran', 'hatao', 'ghar todna', 'jameen khabra',
                'उत्पादन', 'घर तोड़ना', 'अवैध', 'जमीन कब्जा'
            ],
            'noise': [
                'noise', 'loud', 'speaker', 'construction', 'traffic',
                'shor', 'awaaz', 'dhun', 'pollution', 'disturbance',
                'शोर', 'आवाज़', 'ध्वनि', 'प्रदूषण'
            ]
        }
    
    def _load_severity_keywords(self) -> Dict[str, List[str]]:
        """Load severity indicator keywords"""
        return {
            'critical': [
                'danger', 'emergency', 'life threatening', 'accident', 'fire',
                'khatra', 'aatank', 'emergency', 'immediate', 'urgent',
                'खतरा', 'आपातकालीन', 'तुरंत', 'जानलेवा', 'आग'
            ],
            'high': [
                'major', 'large', 'broken', 'collapsed', 'blocked', 'overflow',
                'bada', 'toot gaya', 'tuk gaya', 'bandh ho gaya',
                'बड़ा', 'टूट गया', 'बंद', 'ओवरफ्लो'
            ],
            'medium': [
                'leaking', 'slow', 'partial', 'some', 'moderate',
                'chota', 'dheere dheere', 'kamm', 'thoda',
                'छोटा', 'धीरे', 'कम', 'थोड़ा'
            ],
            'low': [
                'minor', 'small', 'slight', 'request', 'suggestion',
                'chhota', 'request', 'sujhav', 'improvement',
                'छोटा', 'अनुरोध', 'सुझाव', 'सुधार'
            ]
        }
    
    def _load_department_mapping(self) -> Dict[str, Department]:
        """Map categories to responsible departments"""
        return {
            'water': Department.WATER,
            'sanitation': Department.SANITATION,
            'roads': Department.ROADS,
            'electricity': Department.ELECTRICITY,
            'housing': Department.HOUSING,
            'waste': Department.MUNICIPAL,
            'street_lights': Department.ELECTRICITY,
            'drainage': Department.SANITATION,
            'eviction': Department.HOUSING,
            'noise': Department.MUNICIPAL,
            'other': Department.MUNICIPAL
        }
    
    async def extract_features(
        self,
        description: str,
        image_analysis: Optional[Dict[str, Any]] = None
    ) -> ClassificationFeatures:
        """Extract features from text and optional image analysis"""
        
        # Normalize text
        normalized_text = description.lower().strip()
        
        # Extract keywords
        keywords = self._extract_keywords(normalized_text)
        
        # Find urgency indicators
        urgency_indicators = self._find_urgency_indicators(normalized_text)
        
        # Find severity indicators
        severity_indicators = self._find_severity_indicators(normalized_text)
        
        # Category indicators
        category_indicators = self._find_category_indicators(normalized_text)
        
        # Image context if available
        image_context = {}
        if image_analysis:
            image_context = self._extract_image_context(image_analysis)
        
        return ClassificationFeatures(
            keywords=keywords,
            urgency_indicators=urgency_indicators,
            location_context=image_context,
            severity_indicators=severity_indicators,
            category_indicators=category_indicators
        )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as',
            'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his',
            'her', 'our', 'their', 'its', 'who', 'whom', 'whose',
            'what', 'where', 'when', 'why', 'how', 'all', 'both',
            'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'just', 'now', 'here', 'there', 'then',
            'again', 'further', 'once', 'however', 'therefore', 'thus',
            'mere', 'sir', 'please', 'help', 'problem', 'issue'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return list(set(keywords))
    
    def _find_urgency_indicators(self, text: str) -> List[str]:
        """Find urgency indicators in text"""
        urgency_patterns = [
            r'\b(immediate|urgent|emergency|asap|right now|quickly|fast)\b',
            r'\b(जल्दी|तुरंत|आपातकालीन|फौरन)\b',
            r'\b(danger|critical|life threatening|serious)\b',
            r'\b(खतरा|गंभीर|जानलेवा)\b'
        ]
        
        indicators = []
        for pattern in urgency_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            indicators.extend(matches)
        
        return list(set(indicators))
    
    def _find_severity_indicators(self, text: str) -> List[str]:
        """Find severity indicators in text"""
        indicators = []
        
        for severity, keywords in self.severity_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    indicators.append(severity)
                    break  # Take first match for each severity level
        
        return list(set(indicators))
    
    def _find_category_indicators(self, text: str) -> Dict[str, int]:
        """Find category indicators and their counts"""
        indicators = {}
        
        for category, keywords in self.category_keywords.items():
            count = 0
            for keyword in keywords:
                count += text.count(keyword.lower())
            if count > 0:
                indicators[category] = count
        
        return indicators
    
    def _extract_image_context(self, image_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context from image analysis"""
        context = {}
        
        # Extract objects detected
        if 'objects' in image_analysis:
            context['detected_objects'] = image_analysis['objects']
        
        # Extract scene description
        if 'description' in image_analysis:
            context['scene_description'] = image_analysis['description']
        
        # Extract technical details
        if 'technical_details' in image_analysis:
            context.update(image_analysis['technical_details'])
        
        return context
    
    def determine_category(self, features: ClassificationFeatures) -> ComplaintCategory:
        """Determine primary category from features"""
        
        # Count category indicators
        category_scores = features.category_indicators.copy()
        
        # Boost scores based on image context
        if features.location_context.get('detected_objects'):
            for obj in features.location_context['detected_objects']:
                for category, keywords in self.category_keywords.items():
                    if any(keyword in obj.lower() for keyword in keywords):
                        category_scores[category] = category_scores.get(category, 0) + 2
        
        # Select category with highest score
        if category_scores:
            primary_category = max(category_scores, key=category_scores.get)
            try:
                return ComplaintCategory(primary_category)
            except ValueError:
                return ComplaintCategory.OTHER
        
        return ComplaintCategory.OTHER
    
    def determine_severity(self, features: ClassificationFeatures) -> ComplaintSeverity:
        """Determine severity from features"""
        
        # Base severity from text indicators
        severity_scores = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        # Count severity indicators
        for indicator in features.severity_indicators:
            severity_scores[indicator] = severity_scores.get(indicator, 0) + 1
        
        # Boost based on urgency
        if features.urgency_indicators:
            if any(urgent in ' '.join(features.urgency_indicators).lower() 
                   for urgent in ['emergency', 'danger', 'critical', 'urgent']):
                severity_scores['critical'] += 3
                severity_scores['high'] += 2
        
        # Boost based on image context
        if features.location_context.get('scene_description'):
            scene = features.location_context['scene_description'].lower()
            if any(word in scene for word in ['broken', 'collapsed', 'flood', 'overflow']):
                severity_scores['high'] += 2
            elif any(word in scene for word in ['leaking', 'cracked', 'damaged']):
                severity_scores['medium'] += 1
        
        # Select highest severity
        max_severity = max(severity_scores, key=severity_scores.get)
        
        # Map to enum with fallback
        severity_mapping = {
            'critical': ComplaintSeverity.CRITICAL,
            'high': ComplaintSeverity.HIGH,
            'medium': ComplaintSeverity.MEDIUM,
            'low': ComplaintSeverity.LOW
        }
        
        return severity_mapping.get(max_severity, ComplaintSeverity.MEDIUM)
    
    def calculate_confidence(
        self,
        features: ClassificationFeatures,
        category: ComplaintCategory,
        severity: ComplaintSeverity
    ) -> float:
        """Calculate confidence score for classification"""
        
        confidence = 0.5  # Base confidence
        
        # Boost confidence if category has strong indicators
        if features.category_indicators:
            max_category_score = max(features.category_indicators.values())
            confidence += min(max_category_score * 0.1, 0.3)
        
        # Boost confidence if severity indicators found
        if features.severity_indicators:
            confidence += 0.1
        
        # Boost confidence if urgency indicators present
        if features.urgency_indicators:
            confidence += 0.1
        
        # Boost confidence if image context available
        if features.location_context:
            confidence += 0.1
        
        # Cap confidence at 0.95
        return min(confidence, 0.95)
    
    def generate_summary(
        self,
        features: ClassificationFeatures,
        category: ComplaintCategory,
        severity: ComplaintSeverity
    ) -> str:
        """Generate human-readable summary"""
        
        category_desc = {
            'water': 'Water supply issue',
            'sanitation': 'Sanitation and drainage problem',
            'roads': 'Road infrastructure issue',
            'electricity': 'Electricity and lighting problem',
            'housing': 'Housing-related issue',
            'waste': 'Waste management problem',
            'street_lights': 'Street lighting issue',
            'drainage': 'Drainage and waterlogging',
            'eviction': 'Eviction or demolition threat',
            'noise': 'Noise pollution issue',
            'other': 'General civic issue'
        }
        
        severity_desc = {
            'critical': 'Critical - Immediate attention required',
            'high': 'High priority - Urgent action needed',
            'medium': 'Medium priority - Should be addressed soon',
            'low': 'Low priority - Can be scheduled'
        }
        
        base_summary = f"{category_desc.get(category.value, 'Unknown issue')} - {severity_desc.get(severity.value, 'Unknown severity')}"
        
        # Add context from keywords
        if features.keywords:
            key_keywords = [kw for kw in features.keywords[:3] if kw in self.category_keywords.get(category.value, [])]
            if key_keywords:
                base_summary += f". Keywords: {', '.join(key_keywords)}"
        
        return base_summary


# Global classifier instance
_classifier: Optional[ComplaintClassifier] = None


def get_complaint_classifier() -> ComplaintClassifier:
    """Get or create complaint classifier"""
    global _classifier
    
    if not _classifier:
        _classifier = ComplaintClassifier()
    
    return _classifier

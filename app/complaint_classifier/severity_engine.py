"""
Severity assessment engine for complaints
Calculates and adjusts complaint severity based on multiple factors
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

from app.shared.schemas.complaint import ComplaintSeverity
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SeverityFactors:
    """Factors influencing severity assessment"""
    urgency_keywords: List[str]
    health_risk_indicators: List[str]
    safety_risk_indicators: List[str]
    infrastructure_risk_indicators: List[str]
    social_impact_indicators: List[str]
    location_context: Dict[str, Any]
    time_context: Dict[str, Any]


class SeverityEngine:
    """Advanced severity assessment engine"""
    
    def __init__(self):
        self.severity_keywords = self._load_severity_keywords()
        self.risk_indicators = self._load_risk_indicators()
        self.context_weights = self._load_context_weights()
        self.severity_thresholds = self._load_severity_thresholds()
    
    def _load_severity_keywords(self) -> Dict[str, List[str]]:
        """Load severity indicator keywords"""
        return {
            'critical': [
                # English
                'danger', 'dangerous', 'emergency', 'urgent', 'critical',
                'life threatening', 'accident', 'fire', 'explosion',
                'collapse', 'collapsed', 'electrocution', 'poisoning',
                'flood', 'flooding', 'drowning', 'injury', 'injured',
                'death', 'died', 'fatal', 'contagious', 'outbreak',
                'structural', 'unsafe', 'hazard', 'immediate',
                
                # Hindi
                'खतरा', 'खतरनाक', 'आपातकालीन', 'तुरंत', 'गंभीर',
                'जानलेवा', 'दुर्घटना', 'आग', 'विस्फोट',
                'गिरना', 'गिर गया', 'करंट', 'जहर',
                'बाढ़', 'डूबना', 'चोट', 'घायल',
                'मौत', 'मर गया', 'घातक', 'संक्रामक', 'महामारी',
                'संरचनात्मक', 'असुरक्षित', 'जोखिम', 'तत्काल'
            ],
            'high': [
                # English
                'major', 'large', 'huge', 'significant', 'serious',
                'broken', 'damaged', 'destroyed', 'blocked', 'overflow',
                'leaking', 'burst', 'cracked', 'fallen', 'uprooted',
                'no water', 'no electricity', 'no light', 'dark',
                'stuck', 'trapped', 'unusable', 'contaminated',
                
                # Hindi
                'बड़ा', 'विशाल', 'गंभीर', 'महत्वपूर्ण', 'टूटा',
                'क्षतिग्रस्त', 'नष्ट', 'बंद', 'ओवरफ्लो',
                'लीक', 'फट गया', 'दरार', 'गिरा', 'उखड़ गया',
                'पानी नहीं', 'बिजली नहीं', 'रोशनी नहीं', 'अंधेरा',
                'फंसा', 'उपयोग नहीं', 'दूषित'
            ],
            'medium': [
                # English
                'moderate', 'some', 'partial', 'slow', 'dripping',
                'small', 'minor', 'little', 'occasional', 'intermittent',
                'weak', 'low', 'poor', 'bad', 'dirty', 'unclean',
                
                # Hindi
                'मध्यम', 'कुछ', 'आंशिक', 'धीरा', 'टपकता',
                'छोटा', 'कम', 'कमज़ोर', 'गंदा', 'अशुद्ध'
            ],
            'low': [
                # English
                'minor', 'small', 'slight', 'request', 'suggestion',
                'improvement', 'maintenance', 'cleaning', 'repair',
                'beautification', 'enhancement', 'upgrade',
                
                # Hindi
                'नगण्य', 'छोटा', 'हल्का', 'अनुरोध', 'सुझाव',
                'सुधार', 'रखरखाव', 'सफाई', 'मरम्मत',
                'सुंदरता', 'उन्नति', 'अपग्रेड'
            ]
        }
    
    def _load_risk_indicators(self) -> Dict[str, List[str]]:
        """Load risk indicator keywords"""
        return {
            'health': [
                'contaminated', 'polluted', 'sewage', 'garbage', 'waste',
                'mosquito', 'flies', 'rats', 'pests', 'infection',
                'disease', 'fever', 'illness', 'sick', 'medical',
                'hospital', 'medicine', 'doctor', 'health',
                'दूषित', 'प्रदूषित', 'गंदा', 'कचरा', 'मच्छर', 'बीमारी'
            ],
            'safety': [
                'fall', 'slip', 'trip', 'electrocution', 'shock',
                'fire', 'burn', 'injury', 'accident', 'danger',
                'unsafe', 'hazard', 'risk', 'threat',
                'गिरना', 'फिसलना', 'करंट', 'झटका', 'आग',
                'चोट', 'दुर्घटना', 'खतरा', 'असुरक्षित', 'जोखिम'
            ],
            'infrastructure': [
                'collapse', 'structural', 'foundation', 'building',
                'bridge', 'road', 'pole', 'wire', 'pipe', 'tank',
                'damaged', 'broken', 'cracked', 'leaning', 'unstable',
                'ढांचा', 'नींव', 'इमारत', 'पुल', 'खंभा',
                'तार', 'पाइप', 'टैंक', 'क्षतिग्रस्त', 'अस्थिर'
            ],
            'social': [
                'children', 'elderly', 'disabled', 'pregnant',
                'school', 'hospital', 'temple', 'market', 'crowd',
                'public', 'community', 'gathering', 'event',
                'बच्चे', 'बूढ़े', 'विकलांग', 'गर्भवती',
                'स्कूल', 'अस्पताल', 'मंदिर', 'बाज़ार', 'भीड़'
            ]
        }
    
    def _load_context_weights(self) -> Dict[str, float]:
        """Load context weights for severity calculation"""
        return {
            'urgency_keywords': 0.3,
            'risk_indicators': 0.25,
            'location_context': 0.2,
            'time_context': 0.15,
            'social_impact': 0.1
        }
    
    def _load_severity_thresholds(self) -> Dict[str, Tuple[float, float]]:
        """Load severity thresholds"""
        return {
            'critical': (0.8, 1.0),
            'high': (0.6, 0.8),
            'medium': (0.3, 0.6),
            'low': (0.0, 0.3)
        }
    
    def calculate_severity(
        self,
        description: str,
        category: Optional[str] = None,
        location_context: Optional[Dict[str, Any]] = None,
        image_analysis: Optional[Dict[str, Any]] = None,
        time_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ComplaintSeverity, float, Dict[str, Any]]:
        """
        Calculate severity score and return severity level
        
        Args:
            description: Complaint description
            category: Complaint category
            location_context: Location-based context
            image_analysis: Image analysis results
            time_context: Time-based context
            
        Returns:
            Tuple of (severity, confidence_score, analysis_details)
        """
        try:
            # Extract severity factors
            factors = self._extract_severity_factors(
                description,
                location_context,
                image_analysis,
                time_context
            )
            
            # Calculate base severity score
            base_score = self._calculate_base_severity_score(factors)
            
            # Apply category adjustments
            category_adjusted_score = self._apply_category_adjustments(
                base_score, category, factors
            )
            
            # Apply context adjustments
            context_adjusted_score = self._apply_context_adjustments(
                category_adjusted_score, factors
            )
            
            # Apply image-based adjustments
            final_score = self._apply_image_adjustments(
                context_adjusted_score, image_analysis
            )
            
            # Determine severity level
            severity = self._score_to_severity(final_score)
            
            # Calculate confidence
            confidence = self._calculate_confidence(factors, final_score)
            
            # Prepare analysis details
            analysis_details = {
                'base_score': base_score,
                'category_adjusted_score': category_adjusted_score,
                'context_adjusted_score': context_adjusted_score,
                'final_score': final_score,
                'factors': factors,
                'severity': severity.value,
                'confidence': confidence,
                'adjustments_applied': {
                    'category': category_adjusted_score != base_score,
                    'context': context_adjusted_score != category_adjusted_score,
                    'image': final_score != context_adjusted_score
                }
            }
            
            logger.info(
                "Severity calculated",
                severity=severity.value,
                score=final_score,
                confidence=confidence,
                category=category
            )
            
            return severity, confidence, analysis_details
            
        except Exception as e:
            logger.error(f"Severity calculation failed: {e}")
            return ComplaintSeverity.MEDIUM, 0.5, {}
    
    def _extract_severity_factors(
        self,
        description: str,
        location_context: Optional[Dict[str, Any]],
        image_analysis: Optional[Dict[str, Any]],
        time_context: Optional[Dict[str, Any]]
    ) -> SeverityFactors:
        """Extract all severity factors from inputs"""
        
        # Text analysis
        urgency_keywords = self._find_urgency_keywords(description)
        risk_indicators = self._find_risk_indicators(description)
        
        # Location context
        location_factors = self._analyze_location_context(location_context)
        
        # Time context
        time_factors = self._analyze_time_context(time_context)
        
        # Social impact
        social_impact = self._analyze_social_impact(description, location_context)
        
        return SeverityFactors(
            urgency_keywords=urgency_keywords,
            health_risk_indicators=risk_indicators.get('health', []),
            safety_risk_indicators=risk_indicators.get('safety', []),
            infrastructure_risk_indicators=risk_indicators.get('infrastructure', []),
            social_impact_indicators=social_impact,
            location_context=location_factors,
            time_context=time_factors
        )
    
    def _find_urgency_keywords(self, text: str) -> List[str]:
        """Find urgency indicator keywords in text"""
        found_keywords = []
        text_lower = text.lower()
        
        for severity, keywords in self.severity_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.append((severity, keyword))
        
        return found_keywords
    
    def _find_risk_indicators(self, text: str) -> Dict[str, List[str]]:
        """Find risk indicator keywords in text"""
        found_indicators = {}
        text_lower = text.lower()
        
        for risk_type, keywords in self.risk_indicators.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if risk_type not in found_indicators:
                        found_indicators[risk_type] = []
                    found_indicators[risk_type].append(keyword)
        
        return found_indicators
    
    def _analyze_location_context(self, location_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze location-based severity factors"""
        if not location_context:
            return {}
        
        factors = {}
        
        # High-density areas increase severity
        if location_context.get('is_dense_area', False):
            factors['density_boost'] = 0.1
        
        # Slum areas increase severity for basic services
        if location_context.get('is_slum_area', False):
            factors['slum_boost'] = 0.15
        
        # Near schools/hospitals increases severity
        if location_context.get('near_sensitive_location', False):
            factors['sensitive_location_boost'] = 0.1
        
        # Main roads increase severity
        if location_context.get('is_main_road', False):
            factors['main_road_boost'] = 0.05
        
        return factors
    
    def _analyze_time_context(self, time_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze time-based severity factors"""
        if not time_context:
            return {}
        
        factors = {}
        current_hour = datetime.now().hour
        
        # Night time increases severity
        if current_hour >= 22 or current_hour <= 6:
            factors['night_boost'] = 0.1
        
        # Weekend increases severity for some categories
        if datetime.now().weekday() >= 5:  # Saturday or Sunday
            factors['weekend_boost'] = 0.05
        
        # Monsoon season increases severity for drainage/water
        if time_context.get('is_monsoon', False):
            factors['monsoon_boost'] = 0.1
        
        return factors
    
    def _analyze_social_impact(
        self,
        description: str,
        location_context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Analyze social impact indicators"""
        impact_indicators = []
        text_lower = description.lower()
        
        # Check for vulnerable groups
        vulnerable_keywords = [
            'children', 'kids', 'child', 'school', 'बच्चे', 'स्कूल',
            'elderly', 'old', 'senior', 'बूढ़े', 'वृद्ध',
            'disabled', 'handicap', 'विकलांग',
            'pregnant', 'women', 'महिला', 'गर्भवती'
        ]
        
        for keyword in vulnerable_keywords:
            if keyword in text_lower:
                impact_indicators.append(f'vulnerable_{keyword}')
        
        # Check for public gathering places
        public_places = [
            'school', 'hospital', 'temple', 'mosque', 'church',
            'market', 'park', 'playground', 'community',
            'स्कूल', 'अस्पताल', 'मंदिर', 'बाज़ार', 'पार्क'
        ]
        
        for place in public_places:
            if place in text_lower:
                impact_indicators.append(f'public_place_{place}')
        
        return impact_indicators
    
    def _calculate_base_severity_score(self, factors: SeverityFactors) -> float:
        """Calculate base severity score from factors"""
        score = 0.0
        
        # Urgency keywords contribution
        if factors.urgency_keywords:
            urgency_score = 0.0
            for severity, keyword in factors.urgency_keywords:
                if severity == 'critical':
                    urgency_score += 0.4
                elif severity == 'high':
                    urgency_score += 0.3
                elif severity == 'medium':
                    urgency_score += 0.2
                elif severity == 'low':
                    urgency_score += 0.1
            
            score += min(urgency_score, 0.5) * self.context_weights['urgency_keywords']
        
        # Risk indicators contribution
        risk_score = 0.0
        all_risks = (factors.health_risk_indicators + 
                    factors.safety_risk_indicators + 
                    factors.infrastructure_risk_indicators)
        
        if all_risks:
            risk_score = min(len(all_risks) * 0.1, 0.4)
            score += risk_score * self.context_weights['risk_indicators']
        
        # Social impact contribution
        if factors.social_impact_indicators:
            social_score = min(len(factors.social_impact_indicators) * 0.05, 0.3)
            score += social_score * self.context_weights['social_impact']
        
        return min(score, 1.0)
    
    def _apply_category_adjustments(
        self,
        base_score: float,
        category: Optional[str],
        factors: SeverityFactors
    ) -> float:
        """Apply category-specific adjustments"""
        if not category:
            return base_score
        
        # Category-specific severity multipliers
        category_multipliers = {
            'electricity': 1.2,  # Higher impact
            'water': 1.15,
            'sanitation': 1.1,
            'health': 1.25,
            'safety': 1.3,
            'eviction': 1.4,
            'noise': 0.9,  # Lower impact
            'waste': 0.95,
            'roads': 1.05,
            'housing': 1.1,
            'other': 1.0
        }
        
        multiplier = category_multipliers.get(category, 1.0)
        adjusted_score = base_score * multiplier
        
        return min(adjusted_score, 1.0)
    
    def _apply_context_adjustments(
        self,
        score: float,
        factors: SeverityFactors
    ) -> float:
        """Apply context-based adjustments"""
        adjusted_score = score
        
        # Location context adjustments
        location_boosts = factors.location_context.values()
        adjusted_score += sum(location_boosts)
        
        # Time context adjustments
        time_boosts = factors.time_context.values()
        adjusted_score += sum(time_boosts)
        
        return min(adjusted_score, 1.0)
    
    def _apply_image_adjustments(
        self,
        score: float,
        image_analysis: Optional[Dict[str, Any]]
    ) -> float:
        """Apply image-based adjustments"""
        if not image_analysis:
            return score
        
        adjusted_score = score
        
        # Visual severity indicators
        if image_analysis.get('visual_severity') == 'critical':
            adjusted_score += 0.2
        elif image_analysis.get('visual_severity') == 'high':
            adjusted_score += 0.1
        elif image_analysis.get('visual_severity') == 'medium':
            adjusted_score += 0.05
        
        # Image confidence boost
        image_confidence = image_analysis.get('confidence', 0.0)
        if image_confidence > 0.8:
            adjusted_score += 0.05
        
        return min(adjusted_score, 1.0)
    
    def _score_to_severity(self, score: float) -> ComplaintSeverity:
        """Convert severity score to severity level"""
        for severity, (min_score, max_score) in self.severity_thresholds.items():
            if min_score <= score < max_score:
                return ComplaintSeverity(severity)
        
        return ComplaintSeverity.MEDIUM
    
    def _calculate_confidence(
        self,
        factors: SeverityFactors,
        final_score: float
    ) -> float:
        """Calculate confidence in severity assessment"""
        confidence = 0.5  # Base confidence
        
        # More factors = higher confidence
        factor_count = (
            len(factors.urgency_keywords) +
            len(factors.health_risk_indicators) +
            len(factors.safety_risk_indicators) +
            len(factors.infrastructure_risk_indicators) +
            len(factors.social_impact_indicators)
        )
        
        confidence += min(factor_count * 0.05, 0.3)
        
        # Extreme scores have higher confidence
        if final_score > 0.8 or final_score < 0.2:
            confidence += 0.1
        
        return min(confidence, 0.95)
    
    def get_severity_explanation(
        self,
        severity: ComplaintSeverity,
        analysis_details: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation of severity assessment"""
        
        explanations = {
            'critical': "This complaint requires immediate attention as it poses a serious risk to life, health, or safety.",
            'high': "This complaint needs urgent attention as it significantly affects daily life and could worsen if delayed.",
            'medium': "This complaint should be addressed soon as it causes inconvenience to residents.",
            'low': "This complaint is a minor issue that can be scheduled for routine maintenance."
        }
        
        base_explanation = explanations.get(severity.value, explanations['medium'])
        
        # Add specific factors
        factors = analysis_details.get('factors', {})
        factor_explanations = []
        
        if factors.urgency_keywords:
            factor_explanations.append("contains urgency indicators")
        
        if factors.health_risk_indicators:
            factor_explanations.append("poses health risks")
        
        if factors.safety_risk_indicators:
            factor_explanations.append("creates safety hazards")
        
        if factors.social_impact_indicators:
            factor_explanations.append("affects vulnerable groups")
        
        if factor_explanations:
            base_explanation += f" Identified factors: {', '.join(factor_explanations)}."
        
        return base_explanation


# Global severity engine instance
_severity_engine: Optional[SeverityEngine] = None


def get_severity_engine() -> SeverityEngine:
    """Get or create severity engine"""
    global _severity_engine
    
    if not _severity_engine:
        _severity_engine = SeverityEngine()
    
    return _severity_engine

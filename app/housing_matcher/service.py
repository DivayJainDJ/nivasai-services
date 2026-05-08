"""
Production-ready Housing Matcher Service
Matches eligible families with available government housing units
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json
import math

from app.shared.firestore.client import get_firestore_client
from app.shared.gemini.client import get_gemini_client
from app.shared.logging.logger import get_logger
from app.shared.retry.retry_engine import with_retry, DEFAULT_RETRY
from app.shared.schemas.housing import (
    FamilyProfile, HousingUnit, HousingMatch, EligibilityResult,
    MatchScore, HousingPriority
)
from app.shared.geo_utils import GeoUtils
from app.shared.validators.housing_validator import HousingValidator

logger = get_logger(__name__)


class HousingMatcherService:
    """Production-ready housing matching service"""
    
    def __init__(self):
        self.firestore = None
        self.gemini = None
        self.geo_utils = GeoUtils()
        self.validator = HousingValidator()
        self._initialized = False
    
    async def initialize(self):
        """Initialize housing matcher dependencies"""
        self.firestore = await get_firestore_client()
        self.gemini = await get_gemini_client()
        self._initialized = True
        logger.info("HousingMatcherService initialized")
    
    @with_retry(DEFAULT_RETRY)
    async def match_housing_eligibility(
        self,
        family_profile: Dict[str, Any],
        search_radius_km: float = 10.0,
        max_results: int = 10,
        include_unavailable: bool = False
    ) -> List[HousingMatch]:
        """
        Match family profile with available housing units
        
        Args:
            family_profile: Family eligibility and preference data
            search_radius_km: Search radius for housing units
            max_results: Maximum number of matches to return
            include_unavailable: Include unavailable units in results
            
        Returns:
            List of housing matches ranked by eligibility score
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            logger.info(
                "Starting housing eligibility matching",
                family_id=family_profile.get('family_id'),
                search_radius_km=search_radius_km,
                max_results=max_results
            )
            
            start_time = datetime.utcnow()
            
            # Validate family profile
            validation_result = self.validator.validate_family_profile(family_profile)
            if not validation_result.is_valid:
                raise ValueError(f"Invalid family profile: {validation_result.errors}")
            
            # Create structured family profile
            family = FamilyProfile(**family_profile)
            
            # Check basic eligibility
            eligibility = await self._check_basic_eligibility(family)
            if not eligibility.is_eligible:
                logger.info(
                    "Family not eligible for housing",
                    family_id=family.family_id,
                    reasons=eligibility.disqualification_reasons
                )
                return []
            
            # Get available housing units
            available_units = await self._get_available_housing_units(
                family.current_location,
                search_radius_km,
                include_unavailable
            )
            
            if not available_units:
                logger.info(
                    "No housing units found in search area",
                    family_id=family.family_id,
                    search_radius_km=search_radius_km
                )
                return []
            
            # Score and rank matches
            matches = await self._score_and_rank_matches(family, available_units)
            
            # Filter and limit results
            filtered_matches = self._filter_matches(matches, family)
            final_matches = filtered_matches[:max_results]
            
            # Generate explanations and document checklists
            for match in final_matches:
                match.explanation = await self._generate_match_explanation(family, match)
                match.document_checklist = await self._generate_document_checklist(family, match)
                match.application_steps = await self._generate_application_steps(family, match)
            
            # Log matching results
            await self._log_matching_results(family, final_matches)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                "Housing matching completed",
                family_id=family.family_id,
                units_found=len(available_units),
                matches_returned=len(final_matches),
                top_score=final_matches[0].score.overall_score if final_matches else 0,
                processing_time_seconds=processing_time
            )
            
            return final_matches
            
        except Exception as e:
            logger.error(
                "Housing matching failed",
                family_id=family_profile.get('family_id'),
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def _check_basic_eligibility(self, family: FamilyProfile) -> EligibilityResult:
        """Check basic eligibility criteria"""
        try:
            is_eligible = True
            disqualification_reasons = []
            eligibility_score = 0.0
            
            # Income eligibility
            max_income = self._get_max_income_for_category(family.category)
            if family.annual_income > max_income:
                is_eligible = False
                disqualification_reasons.append(f"Income exceeds limit ({max_income})")
            else:
                # Score based on how close to limit
                income_ratio = family.annual_income / max_income
                eligibility_score += (1 - income_ratio) * 30  # 30% weight for income
            
            # Family size eligibility
            if family.family_size < 1:
                is_eligible = False
                disqualification_reasons.append("Invalid family size")
            elif family.family_size > 8:
                is_eligible = False
                disqualification_reasons.append("Family size too large")
            else:
                # Score based on family size appropriateness
                size_score = self._score_family_size(family.family_size)
                eligibility_score += size_score * 20  # 20% weight for family size
            
            # Age eligibility
            if family.primary_applicant_age < 18:
                is_eligible = False
                disqualification_reasons.append("Primary applicant must be 18+")
            elif family.primary_applicant_age > 70:
                is_eligible = False
                disqualification_reasons.append("Primary applicant age too high")
            else:
                # Score based on age
                age_score = self._score_applicant_age(family.primary_applicant_age)
                eligibility_score += age_score * 15  # 15% weight for age
            
            # Residence eligibility
            if not family.has_local_residence:
                is_eligible = False
                disqualification_reasons.append("Must be local resident")
            else:
                eligibility_score += 15  # 15% weight for residence
            
            # Previous housing
            if family.owns_property:
                is_eligible = False
                disqualification_reasons.append("Already owns property")
            else:
                eligibility_score += 10  # 10% weight for not owning property
            
            # Special categories
            special_score = self._score_special_categories(family)
            eligibility_score += special_score * 10  # 10% weight for special categories
            
            return EligibilityResult(
                is_eligible=is_eligible,
                eligibility_score=min(eligibility_score, 100),
                disqualification_reasons=disqualification_reasons,
                eligible_categories=self._get_eligible_categories(family),
                max_income_limit=max_income
            )
            
        except Exception as e:
            logger.error(f"Eligibility check failed: {e}")
            raise
    
    def _get_max_income_for_category(self, category: str) -> float:
        """Get maximum income limit for category"""
        income_limits = {
            'EWS': 300000,      # ₹3 Lakhs
            'LIG': 600000,      # ₹6 Lakhs
            'MIG1': 1200000,    # ₹12 Lakhs
            'MIG2': 1800000,    # ₹18 Lakhs
            'HIG': 2500000      # ₹25 Lakhs
        }
        return income_limits.get(category, 300000)
    
    def _score_family_size(self, family_size: int) -> float:
        """Score family size (0-1, higher = better)"""
        # Optimal family sizes: 2-4 people
        if 2 <= family_size <= 4:
            return 1.0
        elif family_size == 1 or family_size == 5:
            return 0.8
        elif family_size == 6:
            return 0.6
        elif family_size == 7:
            return 0.4
        else:
            return 0.2
    
    def _score_applicant_age(self, age: int) -> float:
        """Score applicant age (0-1, higher = better)"""
        # Optimal age range: 25-60
        if 25 <= age <= 60:
            return 1.0
        elif 18 <= age < 25 or 60 < age <= 65:
            return 0.8
        elif 65 < age <= 70:
            return 0.5
        else:
            return 0.2
    
    def _score_special_categories(self, family: FamilyProfile) -> float:
        """Score special categories (0-1)"""
        score = 0.0
        
        if family.is_senior_citizen:
            score += 0.3
        if family.is_disabled:
            score += 0.4
        if family.is_widow:
            score += 0.3
        if family.is_single_woman:
            score += 0.2
        if family.is_minority:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_eligible_categories(self, family: FamilyProfile) -> List[str]:
        """Get eligible housing categories for family"""
        eligible = []
        
        # Check each category based on income
        categories = ['EWS', 'LIG', 'MIG1', 'MIG2', 'HIG']
        for category in categories:
            max_income = self._get_max_income_for_category(category)
            if family.annual_income <= max_income:
                eligible.append(category)
        
        return eligible
    
    async def _get_available_housing_units(
        self,
        location: Dict[str, float],
        search_radius_km: float,
        include_unavailable: bool
    ) -> List[HousingUnit]:
        """Get available housing units within search radius"""
        try:
            # Query Firestore for housing units
            query = self.firestore.collection('housing_units')
            
            if not include_unavailable:
                query = query.where('status', '==', 'available')
            
            # Get all units (would ideally use geoqueries)
            docs = await query.get()
            
            units = []
            for doc in docs:
                unit_data = doc.to_dict()
                
                # Check if unit is within search radius
                unit_location = unit_data.get('location', {})
                if not unit_location:
                    continue
                
                distance = self.geo_utils.calculate_distance(
                    location['lat'], location['lng'],
                    unit_location['lat'], unit_location['lng']
                )
                
                if distance <= search_radius_km:
                    unit_data['id'] = doc.id
                    unit_data['distance_km'] = distance
                    units.append(HousingUnit(**unit_data))
            
            # Sort by distance
            units.sort(key=lambda x: x.distance_km)
            
            logger.info(
                "Housing units found",
                total_units=len(units),
                search_radius_km=search_radius_km
            )
            
            return units
            
        except Exception as e:
            logger.error(f"Failed to get housing units: {e}")
            return []
    
    async def _score_and_rank_matches(
        self,
        family: FamilyProfile,
        units: List[HousingUnit]
    ) -> List[HousingMatch]:
        """Score and rank housing matches"""
        matches = []
        
        for unit in units:
            try:
                # Calculate match scores
                scores = await self._calculate_match_scores(family, unit)
                
                # Create match object
                match = HousingMatch(
                    family_id=family.family_id,
                    unit_id=unit.id,
                    unit=unit,
                    score=scores,
                    matched_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                
                matches.append(match)
                
            except Exception as e:
                logger.error(f"Failed to score unit {unit.id}: {e}")
                continue
        
        # Sort by overall score (descending)
        matches.sort(key=lambda x: x.score.overall_score, reverse=True)
        
        return matches
    
    async def _calculate_match_scores(self, family: FamilyProfile, unit: HousingUnit) -> MatchScore:
        """Calculate detailed match scores"""
        try:
            # Eligibility score (40% weight)
            eligibility_score = await self._calculate_eligibility_score(family, unit)
            
            # Distance score (20% weight)
            distance_score = self._calculate_distance_score(family, unit)
            
            # Size fit score (15% weight)
            size_score = self._calculate_size_fit_score(family, unit)
            
            # Preference score (15% weight)
            preference_score = self._calculate_preference_score(family, unit)
            
            # Availability score (10% weight)
            availability_score = self._calculate_availability_score(unit)
            
            # Calculate overall score
            overall_score = (
                eligibility_score * 0.4 +
                distance_score * 0.2 +
                size_score * 0.15 +
                preference_score * 0.15 +
                availability_score * 0.1
            )
            
            return MatchScore(
                eligibility_score=round(eligibility_score, 2),
                distance_score=round(distance_score, 2),
                size_fit_score=round(size_score, 2),
                preference_score=round(preference_score, 2),
                availability_score=round(availability_score, 2),
                overall_score=round(overall_score, 2)
            )
            
        except Exception as e:
            logger.error(f"Score calculation failed: {e}")
            return MatchScore(
                eligibility_score=0.0,
                distance_score=0.0,
                size_fit_score=0.0,
                preference_score=0.0,
                availability_score=0.0,
                overall_score=0.0
            )
    
    async def _calculate_eligibility_score(self, family: FamilyProfile, unit: HousingUnit) -> float:
        """Calculate eligibility score for specific unit"""
        try:
            score = 0.0
            
            # Category match
            if family.category in unit.eligible_categories:
                score += 40
            else:
                score += 0
            
            # Income match
            if family.annual_income <= unit.max_income:
                income_ratio = family.annual_income / unit.max_income
                score += (1 - income_ratio) * 30
            else:
                score += 0
            
            # Family size match
            if unit.min_bedrooms <= self._get_required_bedrooms(family.family_size) <= unit.max_bedrooms:
                score += 20
            else:
                score += 0
            
            # Special category match
            if any(unit.special_categories.get(cat, False) for cat in family.special_categories):
                score += 10
            else:
                score += 5
            
            return min(score, 100)
            
        except Exception as e:
            logger.error(f"Eligibility scoring failed: {e}")
            return 0.0
    
    def _calculate_distance_score(self, family: FamilyProfile, unit: HousingUnit) -> float:
        """Calculate distance-based score"""
        # Closer is better
        if unit.distance_km <= 2:
            return 100
        elif unit.distance_km <= 5:
            return 80
        elif unit.distance_km <= 10:
            return 60
        elif unit.distance_km <= 15:
            return 40
        else:
            return 20
    
    def _calculate_size_fit_score(self, family: FamilyProfile, unit: HousingUnit) -> float:
        """Calculate size fit score"""
        required_bedrooms = self._get_required_bedrooms(family.family_size)
        
        if unit.bedrooms == required_bedrooms:
            return 100
        elif unit.bedrooms == required_bedrooms + 1:
            return 90
        elif unit.bedrooms == required_bedrooms - 1:
            return 70
        elif unit.bedrooms > required_bedrooms + 1:
            return 50
        else:
            return 30
    
    def _calculate_preference_score(self, family: FamilyProfile, unit: HousingUnit) -> float:
        """Calculate preference-based score"""
        score = 0.0
        
        # Location preference
        if family.preferred_localities and unit.locality in family.preferred_localities:
            score += 40
        else:
            score += 20
        
        # Floor preference
        if family.preferred_floor_range:
            min_floor, max_floor = family.preferred_floor_range
            if min_floor <= unit.floor_number <= max_floor:
                score += 30
            else:
                score += 10
        else:
            score += 20
        
        # Amenities preference
        if family.required_amenities:
            matching_amenities = set(family.required_amenities) & set(unit.amenities)
            score += (len(matching_amenities) / len(family.required_amenities)) * 30
        else:
            score += 15
        
        return min(score, 100)
    
    def _calculate_availability_score(self, unit: HousingUnit) -> float:
        """Calculate availability score"""
        if unit.status == 'available':
            return 100
        elif unit.status == 'reserved':
            return 50
        else:
            return 0
    
    def _get_required_bedrooms(self, family_size: int) -> int:
        """Get required bedrooms based on family size"""
        if family_size <= 2:
            return 1
        elif family_size <= 4:
            return 2
        elif family_size <= 6:
            return 3
        else:
            return 4
    
    def _filter_matches(self, matches: List[HousingMatch], family: FamilyProfile) -> List[HousingMatch]:
        """Filter matches based on family requirements"""
        filtered = []
        
        for match in matches:
            # Minimum score threshold
            if match.score.overall_score < 30:
                continue
            
            # Must meet basic eligibility
            if match.score.eligibility_score < 50:
                continue
            
            # Must have required bedrooms
            required_bedrooms = self._get_required_bedrooms(family.family_size)
            if not (match.unit.min_bedrooms <= required_bedrooms <= match.unit.max_bedrooms):
                continue
            
            filtered.append(match)
        
        return filtered
    
    async def _generate_match_explanation(self, family: FamilyProfile, match: HousingMatch) -> str:
        """Generate explanation for why this match is good"""
        try:
            # Use Gemini to generate personalized explanation
            prompt = f"""
            Generate a personalized explanation in both English and Hindi for why this housing unit is a good match for the family.
            
            Family Profile:
            - Family Size: {family.family_size}
            - Category: {family.category}
            - Annual Income: ₹{family.annual_income:,}
            - Current Location: {family.current_location}
            
            Housing Unit:
            - Type: {match.unit.type}
            - Bedrooms: {match.unit.bedrooms}
            - Area: {match.unit.area_sqft} sqft
            - Location: {match.unit.locality}
            - Distance: {match.unit.distance_km} km
            - Monthly Cost: ₹{match.unit.monthly_cost:,}
            
            Match Score: {match.score.overall_score}/100
            
            Explain in simple terms why this is a good match, focusing on:
            1. Eligibility (income, category match)
            2. Size suitability
            3. Location convenience
            4. Affordability
            
            Provide the explanation in both English and Hindi.
            """
            
            response = await self.gemini.generate_text(prompt, temperature=0.3)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            return "This housing unit matches your eligibility criteria and family size requirements."
    
    async def _generate_document_checklist(self, family: FamilyProfile, match: HousingMatch) -> List[str]:
        """Generate document checklist for application"""
        try:
            # Base documents for all categories
            base_docs = [
                "Aadhaar card for all family members",
                "PAN card of primary applicant",
                "Income certificate (last 6 months)",
                "Residence proof (voter ID/ration card)",
                "Bank account details",
                "Passport size photographs (4 per member)"
            ]
            
            # Category-specific documents
            category_docs = {
                'EWS': ["Income certificate below ₹3 lakh"],
                'LIG': ["Income certificate below ₹6 lakh"],
                'MIG1': ["Income certificate below ₹12 lakh"],
                'MIG2': ["Income certificate below ₹18 lakh"],
                'HIG': ["Income certificate below ₹25 lakh"]
            }
            
            # Special category documents
            special_docs = []
            if family.is_senior_citizen:
                special_docs.append("Age proof for senior citizen")
            if family.is_disabled:
                special_docs.append("Disability certificate")
            if family.is_widow:
                special_docs.append("Widow certificate")
            if family.is_minority:
                special_docs.append("Minority community certificate")
            
            # Combine all documents
            all_docs = base_docs + category_docs.get(family.category, []) + special_docs
            
            return all_docs
            
        except Exception as e:
            logger.error(f"Document checklist generation failed: {e}")
            return base_docs
    
    async def _generate_application_steps(self, family: FamilyProfile, match: HousingMatch) -> List[str]:
        """Generate step-by-step application process"""
        return [
            "1. Visit the housing authority office with all required documents",
            "2. Fill out the application form (available online and offline)",
            "3. Submit documents for verification",
            "4. Pay application fee (₹500-1000 depending on category)",
            "5. Wait for eligibility verification (2-4 weeks)",
            "6. Receive allotment letter if selected",
            "7. Complete payment formalities within 30 days",
            "8. Take possession of housing unit"
        ]
    
    async def _log_matching_results(self, family: FamilyProfile, matches: List[HousingMatch]) -> None:
        """Log matching results for analytics"""
        try:
            log_entry = {
                'family_id': family.family_id,
                'category': family.category,
                'family_size': family.family_size,
                'annual_income': family.annual_income,
                'search_location': family.current_location,
                'matches_found': len(matches),
                'top_score': matches[0].score.overall_score if matches else 0,
                'average_score': sum(m.score.overall_score for m in matches) / len(matches) if matches else 0,
                'matched_at': datetime.utcnow().isoformat()
            }
            
            await self.firestore.collection('housing_match_logs').add(log_entry)
            
        except Exception as e:
            logger.error(f"Failed to log matching results: {e}")
    
    async def track_application_status(self, family_id: str, unit_id: str) -> Dict[str, Any]:
        """Track application status for a specific match"""
        try:
            # Get application record
            application_query = self.firestore.collection('housing_applications').where(
                'family_id', '==', family_id
            ).where('unit_id', '==', unit_id).get()
            
            if not application_query.docs:
                return {'status': 'not_applied', 'message': 'No application found'}
            
            application = application_query.docs[0].to_dict()
            
            return {
                'status': application.get('status', 'unknown'),
                'applied_at': application.get('applied_at'),
                'last_updated': application.get('updated_at'),
                'current_stage': application.get('current_stage'),
                'next_steps': application.get('next_steps'),
                'documents_pending': application.get('documents_pending', []),
                'estimated_completion': application.get('estimated_completion')
            }
            
        except Exception as e:
            logger.error(f"Failed to track application status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def update_housing_preferences(
        self,
        family_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update family housing preferences"""
        try:
            await self.firestore.collection('family_profiles').document(family_id).update({
                'preferred_localities': preferences.get('preferred_localities', []),
                'preferred_floor_range': preferences.get('preferred_floor_range'),
                'required_amenities': preferences.get('required_amenities', []),
                'max_monthly_cost': preferences.get('max_monthly_cost'),
                'updated_at': datetime.utcnow().isoformat()
            })
            
            return {'success': True, 'message': 'Preferences updated successfully'}
            
        except Exception as e:
            logger.error(f"Failed to update preferences: {e}")
            return {'success': False, 'message': str(e)}


# Global service instance
_housing_matcher: Optional[HousingMatcherService] = None


async def get_housing_matcher() -> HousingMatcherService:
    """Get or create housing matcher service"""
    global _housing_matcher
    
    if not _housing_matcher:
        _housing_matcher = HousingMatcherService()
        await _housing_matcher.initialize()
    
    return _housing_matcher


async def initialize_housing_matcher():
    """Initialize housing matcher service"""
    await get_housing_matcher()

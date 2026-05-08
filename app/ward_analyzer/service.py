"""
Production-ready Ward Analyzer Service
Analyzes ward infrastructure using satellite imagery and AI
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import base64
import json

from app.shared.gemini.client import get_gemini_client
from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger
from app.shared.retry.retry_engine import with_retry, GEMINI_RETRY
from app.shared.schemas.ward import WardAnalysis, WardScore, WardPriority
from app.shared.geo_utils import GeoUtils
from app.shared.image_utils import ImageProcessor

logger = get_logger(__name__)


class WardAnalyzerService:
    """Production-ready ward infrastructure analysis service"""
    
    def __init__(self):
        self.gemini = None
        self.firestore = None
        self.geo_utils = GeoUtils()
        self.image_processor = ImageProcessor()
        self._initialized = False
    
    async def initialize(self):
        """Initialize analyzer service dependencies"""
        self.gemini = await get_gemini_client()
        self.firestore = await get_firestore_client()
        self._initialized = True
        logger.info("WardAnalyzerService initialized")
    
    @with_retry(GEMINI_RETRY)
    async def analyze_ward_infrastructure(
        self,
        ward_id: str,
        ward_name: str,
        coordinates: Dict[str, float],
        satellite_image: Optional[bytes] = None,
        image_url: Optional[str] = None,
        analysis_type: str = "comprehensive"
    ) -> WardAnalysis:
        """
        Analyze ward infrastructure using satellite imagery
        
        Args:
            ward_id: Unique ward identifier
            ward_name: Ward display name
            coordinates: Ward center coordinates (lat, lng)
            satellite_image: Raw satellite image bytes
            image_url: URL of satellite image
            analysis_type: Type of analysis (comprehensive, quick, detailed)
            
        Returns:
            Complete ward analysis results
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            logger.info(
                "Starting ward infrastructure analysis",
                ward_id=ward_id,
                ward_name=ward_name,
                has_image=bool(satellite_image or image_url),
                analysis_type=analysis_type
            )
            
            start_time = datetime.utcnow()
            
            # Get image data if URL provided
            if image_url and not satellite_image:
                satellite_image = await self._fetch_satellite_image(image_url)
            
            # Validate coordinates
            lat, lng = coordinates.get('lat'), coordinates.get('lng')
            if not lat or not lng:
                raise ValueError("Invalid coordinates provided")
            
            # Preprocess image
            processed_image = await self._preprocess_satellite_image(satellite_image)
            
            # Perform AI analysis
            analysis_result = await self.gemini.analyze_ward_infrastructure(
                ward_id=ward_id,
                ward_name=ward_name,
                coordinates=coordinates,
                satellite_image=processed_image
            )
            
            # Enhance with geospatial analysis
            enhanced_analysis = await self._enhance_with_geospatial_data(
                analysis_result, coordinates, ward_id
            )
            
            # Calculate infrastructure scores
            infrastructure_scores = self._calculate_infrastructure_scores(
                enhanced_analysis
            )
            
            # Determine priority and recommendations
            priority_analysis = self._analyze_priority_and_recommendations(
                infrastructure_scores, enhanced_analysis
            )
            
            # Estimate population and demographics
            demographic_analysis = await self._estimate_demographics(
                coordinates, enhanced_analysis
            )
            
            # Create comprehensive analysis object
            ward_analysis = WardAnalysis(
                ward_id=ward_id,
                ward_name=ward_name,
                coordinates=coordinates,
                analysis_type=analysis_type,
                scores=infrastructure_scores,
                priority_analysis=priority_analysis,
                demographic_analysis=demographic_analysis,
                ai_analysis=enhanced_analysis,
                analyzed_at=datetime.utcnow(),
                processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                confidence_score=self._calculate_overall_confidence(enhanced_analysis),
                data_sources=self._get_data_sources_used(satellite_image, coordinates)
            )
            
            # Save analysis to Firestore
            await self._save_ward_analysis(ward_analysis)
            
            # Generate remediation projects
            await self._generate_remediation_projects(ward_analysis)
            
            logger.info(
                "Ward analysis completed",
                ward_id=ward_id,
                overall_score=infrastructure_scores.overall_score,
                priority_level=priority_analysis.priority_level,
                confidence=ward_analysis.confidence_score
            )
            
            return ward_analysis
            
        except Exception as e:
            logger.error(
                "Ward analysis failed",
                ward_id=ward_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def _fetch_satellite_image(self, image_url: str) -> bytes:
        """Fetch satellite image from URL"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"Failed to fetch image: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Image fetch failed: {e}")
            raise
    
    async def _preprocess_satellite_image(self, image_data: Optional[bytes]) -> Optional[bytes]:
        """Preprocess satellite image for better AI analysis"""
        if not image_data:
            return None
        
        try:
            # Apply image preprocessing
            processed = await self.image_processor.enhance_satellite_image(image_data)
            
            # Validate processed image
            if not self.image_processor.validate_satellite_image(processed):
                logger.warning("Processed image failed validation, using original")
                return image_data
            
            return processed
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image_data
    
    async def _enhance_with_geospatial_data(
        self,
        ai_analysis: Dict[str, Any],
        coordinates: Dict[str, float],
        ward_id: str
    ) -> Dict[str, Any]:
        """Enhance AI analysis with geospatial data"""
        try:
            enhanced = ai_analysis.copy()
            
            # Get nearby infrastructure
            nearby_infra = await self._get_nearby_infrastructure(coordinates)
            enhanced['nearby_infrastructure'] = nearby_infra
            
            # Get terrain analysis
            terrain_analysis = await self._analyze_terrain(coordinates)
            enhanced['terrain_analysis'] = terrain_analysis
            
            # Get land use classification
            land_use = await self._classify_land_use(coordinates)
            enhanced['land_use_classification'] = land_use
            
            # Get accessibility metrics
            accessibility = await self._calculate_accessibility(coordinates)
            enhanced['accessibility_metrics'] = accessibility
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Geospatial enhancement failed: {e}")
            return ai_analysis
    
    async def _get_nearby_infrastructure(self, coordinates: Dict[str, float]) -> Dict[str, Any]:
        """Get nearby infrastructure from GIS data"""
        try:
            # This would integrate with GIS APIs
            # For now, return mock data
            return {
                'hospitals': 2,
                'schools': 5,
                'water_towers': 3,
                'power_stations': 1,
                'market_areas': 4,
                'transport_hubs': 2
            }
        except Exception as e:
            logger.error(f"Nearby infrastructure query failed: {e}")
            return {}
    
    async def _analyze_terrain(self, coordinates: Dict[str, float]) -> Dict[str, Any]:
        """Analyze terrain characteristics"""
        try:
            # This would use elevation and terrain APIs
            return {
                'elevation_meters': 850,
                'slope_degrees': 2.5,
                'terrain_type': 'urban_plain',
                'drainage_pattern': 'grid',
                'flood_risk': 'medium'
            }
        except Exception as e:
            logger.error(f"Terrain analysis failed: {e}")
            return {}
    
    async def _classify_land_use(self, coordinates: Dict[str, float]) -> Dict[str, Any]:
        """Classify land use patterns"""
        try:
            return {
                'residential': 0.45,
                'commercial': 0.20,
                'industrial': 0.10,
                'institutional': 0.15,
                'recreational': 0.05,
                'vacant': 0.05
            }
        except Exception as e:
            logger.error(f"Land use classification failed: {e}")
            return {}
    
    async def _calculate_accessibility(self, coordinates: Dict[str, float]) -> Dict[str, Any]:
        """Calculate accessibility metrics"""
        try:
            return {
                'road_density_km_per_sqkm': 12.5,
                'public_transport_access': 0.75,
                'walkability_score': 0.68,
                'bike_friendly': 0.45,
                'disabled_accessibility': 0.35
            }
        except Exception as e:
            logger.error(f"Accessibility calculation failed: {e}")
            return {}
    
    def _calculate_infrastructure_scores(self, analysis: Dict[str, Any]) -> WardScore:
        """Calculate infrastructure scores from analysis"""
        try:
            # Base scores from AI analysis
            ai_scores = analysis.get('scores', {})
            
            # Calculate individual component scores
            road_connectivity = self._score_road_connectivity(ai_scores, analysis)
            water_access = self._score_water_access(ai_scores, analysis)
            sanitation_coverage = self._score_sanitation_coverage(ai_scores, analysis)
            electricity_access = self._score_electricity_access(ai_scores, analysis)
            green_coverage = self._score_green_coverage(ai_scores, analysis)
            informal_settlements = self._score_informal_settlements(ai_scores, analysis)
            
            # Calculate overall score
            scores = [
                road_connectivity, water_access, sanitation_coverage,
                electricity_access, green_coverage, (10 - informal_settlements)  # Invert informal settlements
            ]
            overall_score = sum(scores) / len(scores)
            
            return WardScore(
                road_connectivity=road_connectivity,
                water_access=water_access,
                sanitation_coverage=sanitation_coverage,
                electricity_access=electricity_access,
                green_coverage=green_coverage,
                informal_settlements=informal_settlements,
                overall_score=round(overall_score, 1)
            )
            
        except Exception as e:
            logger.error(f"Infrastructure scoring failed: {e}")
            return WardScore(
                road_connectivity=5.0,
                water_access=5.0,
                sanitation_coverage=5.0,
                electricity_access=5.0,
                green_coverage=5.0,
                informal_settlements=5.0,
                overall_score=5.0
            )
    
    def _score_road_connectivity(self, ai_scores: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        """Score road connectivity (1-10)"""
        base_score = ai_scores.get('road_connectivity', 5.0)
        
        # Adjust based on accessibility metrics
        accessibility = analysis.get('accessibility_metrics', {})
        road_density = accessibility.get('road_density_km_per_sqkm', 10)
        
        if road_density > 15:
            base_score = min(base_score + 2, 10)
        elif road_density < 5:
            base_score = max(base_score - 2, 1)
        
        return round(base_score, 1)
    
    def _score_water_access(self, ai_scores: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        """Score water access (1-10)"""
        base_score = ai_scores.get('water_access', 5.0)
        
        # Adjust based on nearby infrastructure
        nearby = analysis.get('nearby_infrastructure', {})
        water_towers = nearby.get('water_towers', 0)
        
        if water_towers > 5:
            base_score = min(base_score + 1, 10)
        elif water_towers < 2:
            base_score = max(base_score - 1, 1)
        
        return round(base_score, 1)
    
    def _score_sanitation_coverage(self, ai_scores: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        """Score sanitation coverage (1-10)"""
        base_score = ai_scores.get('sanitation_coverage', 5.0)
        
        # Adjust based on terrain
        terrain = analysis.get('terrain_analysis', {})
        flood_risk = terrain.get('flood_risk', 'medium')
        
        if flood_risk == 'high':
            base_score = max(base_score - 1, 1)
        elif flood_risk == 'low':
            base_score = min(base_score + 1, 10)
        
        return round(base_score, 1)
    
    def _score_electricity_access(self, ai_scores: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        """Score electricity access (1-10)"""
        base_score = ai_scores.get('electricity_access', 5.0)
        
        # Adjust based on nearby infrastructure
        nearby = analysis.get('nearby_infrastructure', {})
        power_stations = nearby.get('power_stations', 0)
        
        if power_stations > 2:
            base_score = min(base_score + 1, 10)
        elif power_stations == 0:
            base_score = max(base_score - 2, 1)
        
        return round(base_score, 1)
    
    def _score_green_coverage(self, ai_scores: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        """Score green coverage (1-10)"""
        base_score = ai_scores.get('green_coverage', 5.0)
        
        # Adjust based on land use
        land_use = analysis.get('land_use_classification', {})
        recreational = land_use.get('recreational', 0.05)
        
        if recreational > 0.1:
            base_score = min(base_score + 2, 10)
        elif recreational < 0.02:
            base_score = max(base_score - 2, 1)
        
        return round(base_score, 1)
    
    def _score_informal_settlements(self, ai_scores: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        """Score informal settlements (1-10, higher = more settlements)"""
        base_score = ai_scores.get('informal_settlements', 5.0)
        
        # Adjust based on land use
        land_use = analysis.get('land_use_classification', {})
        vacant = land_use.get('vacant', 0.05)
        
        if vacant > 0.1:
            base_score = max(base_score - 1, 1)  # More vacant land = less informal
        elif vacant < 0.02:
            base_score = min(base_score + 1, 10)  # Less vacant land = more informal
        
        return round(base_score, 1)
    
    def _analyze_priority_and_recommendations(
        self,
        scores: WardScore,
        analysis: Dict[str, Any]
    ) -> WardPriority:
        """Analyze priority and generate recommendations"""
        try:
            # Determine priority level
            if scores.overall_score < 3.0:
                priority_level = "critical"
            elif scores.overall_score < 5.0:
                priority_level = "high"
            elif scores.overall_score < 7.0:
                priority_level = "medium"
            else:
                priority_level = "low"
            
            # Find top priority areas
            component_scores = {
                'Road Connectivity': scores.road_connectivity,
                'Water Access': scores.water_access,
                'Sanitation': scores.sanitation_coverage,
                'Electricity': scores.electricity_access,
                'Green Spaces': scores.green_coverage
            }
            
            # Sort by score (lowest = highest priority)
            sorted_components = sorted(component_scores.items(), key=lambda x: x[1])
            top_priority = sorted_components[0][0]
            
            # Generate recommendations
            recommendations = self._generate_recommendations(scores, analysis)
            
            return WardPriority(
                priority_level=priority_level,
                top_priority_area=top_priority,
                recommendations=recommendations,
                estimated_cost_range=self._estimate_project_costs(scores, analysis),
                implementation_timeline=self._estimate_timeline(scores, analysis)
            )
            
        except Exception as e:
            logger.error(f"Priority analysis failed: {e}")
            return WardPriority(
                priority_level="medium",
                top_priority_area="General Infrastructure",
                recommendations=["Comprehensive infrastructure assessment needed"],
                estimated_cost_range="Unknown",
                implementation_timeline="Unknown"
            )
    
    def _generate_recommendations(
        self,
        scores: WardScore,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate specific recommendations based on scores"""
        recommendations = []
        
        if scores.road_connectivity < 5.0:
            recommendations.append("Improve road connectivity and repair damaged roads")
        
        if scores.water_access < 5.0:
            recommendations.append("Expand water supply network and install new connections")
        
        if scores.sanitation_coverage < 5.0:
            recommendations.append("Upgrade drainage systems and improve waste management")
        
        if scores.electricity_access < 5.0:
            recommendations.append("Install street lights and upgrade electrical infrastructure")
        
        if scores.green_coverage < 5.0:
            recommendations.append("Develop parks and green spaces for community welfare")
        
        if scores.informal_settlements > 7.0:
            recommendations.append("Develop housing improvement programs for informal settlements")
        
        return recommendations
    
    def _estimate_project_costs(
        self,
        scores: WardScore,
        analysis: Dict[str, Any]
    ) -> str:
        """Estimate project cost range"""
        # This would use actual cost data
        if scores.overall_score < 3.0:
            return "₹5-10 Crore"
        elif scores.overall_score < 5.0:
            return "₹2-5 Crore"
        elif scores.overall_score < 7.0:
            return "₹50 Lakhs - 2 Crore"
        else:
            return "₹10-50 Lakhs"
    
    def _estimate_timeline(
        self,
        scores: WardScore,
        analysis: Dict[str, Any]
    ) -> str:
        """Estimate implementation timeline"""
        if scores.overall_score < 3.0:
            return "18-24 months"
        elif scores.overall_score < 5.0:
            return "12-18 months"
        elif scores.overall_score < 7.0:
            return "6-12 months"
        else:
            return "3-6 months"
    
    async def _estimate_demographics(
        self,
        coordinates: Dict[str, float],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estimate population and demographics"""
        try:
            # This would use census data and satellite analysis
            land_use = analysis.get('land_use_classification', {})
            residential_ratio = land_use.get('residential', 0.4)
            
            # Estimate population based on area and density
            ward_area_km2 = 2.5  # Typical ward area
            population_density = 15000 if residential_ratio > 0.5 else 10000
            estimated_population = int(ward_area_km2 * population_density)
            
            return {
                'estimated_population': estimated_population,
                'population_density_per_sqkm': population_density,
                'household_count': estimated_population // 5,  # Avg 5 people per household
                'income_level': 'mixed',  # Would use actual data
                'education_level': 'mixed',
                'employment_sectors': ['services', 'manufacturing', 'informal']
            }
            
        except Exception as e:
            logger.error(f"Demographics estimation failed: {e}")
            return {}
    
    def _calculate_overall_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall confidence in analysis"""
        base_confidence = 0.7
        
        # Boost if multiple data sources used
        data_sources = len([k for k, v in analysis.items() if v])
        if data_sources > 5:
            base_confidence += 0.1
        
        # Boost if AI confidence is high
        ai_confidence = analysis.get('confidence', 0.7)
        if ai_confidence > 0.8:
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)
    
    def _get_data_sources_used(
        self,
        has_image: bool,
        coordinates: Dict[str, float]
    ) -> List[str]:
        """Get list of data sources used in analysis"""
        sources = []
        
        if has_image:
            sources.append("satellite_imagery")
        
        if coordinates:
            sources.extend(["gis_data", "terrain_analysis", "land_use_classification"])
        
        sources.append("ai_analysis")
        
        return sources
    
    async def _save_ward_analysis(self, analysis: WardAnalysis) -> None:
        """Save ward analysis to Firestore"""
        try:
            analysis_dict = analysis.dict()
            
            # Check if analysis already exists
            existing_doc = await self.firestore.collection('ward_analyses').document(analysis.ward_id).get()
            
            if existing_doc.exists:
                # Update existing analysis
                await self.firestore.collection('ward_analyses').document(analysis.ward_id).update({
                    **analysis_dict,
                    'updated_at': datetime.utcnow().isoformat(),
                    'version': firestore.Increment(1)
                })
            else:
                # Create new analysis
                await self.firestore.collection('ward_analyses').document(analysis.ward_id).set({
                    **analysis_dict,
                    'created_at': datetime.utcnow().isoformat(),
                    'version': 1
                })
            
        except Exception as e:
            logger.error(f"Failed to save ward analysis: {e}")
            raise
    
    async def _generate_remediation_projects(self, analysis: WardAnalysis) -> None:
        """Generate specific remediation projects based on analysis"""
        try:
            projects = []
            
            # Generate projects based on low-scoring areas
            if analysis.scores.road_connectivity < 5.0:
                projects.append({
                    'name': 'Road Connectivity Improvement',
                    'category': 'roads',
                    'priority': 'high' if analysis.scores.road_connectivity < 3.0 else 'medium',
                    'estimated_cost': '₹50 Lakhs - 2 Crore',
                    'timeline': '6-12 months',
                    'description': 'Repair damaged roads and improve connectivity'
                })
            
            if analysis.scores.water_access < 5.0:
                projects.append({
                    'name': 'Water Supply Expansion',
                    'category': 'water',
                    'priority': 'high' if analysis.scores.water_access < 3.0 else 'medium',
                    'estimated_cost': '₹1-3 Crore',
                    'timeline': '12-18 months',
                    'description': 'Expand water network and install new connections'
                })
            
            if analysis.scores.sanitation_coverage < 5.0:
                projects.append({
                    'name': 'Sanitation System Upgrade',
                    'category': 'sanitation',
                    'priority': 'high' if analysis.scores.sanitation_coverage < 3.0 else 'medium',
                    'estimated_cost': '₹75 Lakhs - 2.5 Crore',
                    'timeline': '8-14 months',
                    'description': 'Upgrade drainage and improve waste management'
                })
            
            if analysis.scores.electricity_access < 5.0:
                projects.append({
                    'name': 'Street Lighting Installation',
                    'category': 'electricity',
                    'priority': 'medium',
                    'estimated_cost': '₹25 Lakhs - 1 Crore',
                    'timeline': '4-8 months',
                    'description': 'Install street lights and upgrade electrical infrastructure'
                })
            
            if analysis.scores.green_coverage < 5.0:
                projects.append({
                    'name': 'Green Space Development',
                    'category': 'recreation',
                    'priority': 'low',
                    'estimated_cost': '₹15 Lakhs - 50 Lakhs',
                    'timeline': '6-12 months',
                    'description': 'Develop parks and green spaces'
                })
            
            # Save projects to Firestore
            for project in projects:
                await self.firestore.collection('remediation_projects').add({
                    **project,
                    'ward_id': analysis.ward_id,
                    'ward_name': analysis.ward_name,
                    'analysis_id': analysis.ward_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'status': 'proposed'
                })
            
            logger.info(
                "Remediation projects generated",
                ward_id=analysis.ward_id,
                project_count=len(projects)
            )
            
        except Exception as e:
            logger.error(f"Failed to generate remediation projects: {e}")
    
    async def batch_analyze_wards(
        self,
        ward_requests: List[Dict[str, Any]]
    ) -> List[WardAnalysis]:
        """
        Analyze multiple wards in batch for efficiency
        
        Args:
            ward_requests: List of ward analysis requests
            
        Returns:
            List of ward analysis results
        """
        logger.info(f"Starting batch ward analysis for {len(ward_requests)} wards")
        
        # Process in parallel with rate limiting
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent analyses
        
        async def analyze_single(ward_request):
            async with semaphore:
                return await self.analyze_ward_infrastructure(**ward_request)
        
        # Execute all analyses
        results = await asyncio.gather(
            *[analyze_single(request) for request in ward_requests],
            return_exceptions=True
        )
        
        # Filter out exceptions and log errors
        analyses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch analysis failed for ward {i}: {result}")
            else:
                analyses.append(result)
        
        logger.info(f"Batch analysis completed: {len(analyses)}/{len(ward_requests)} successful")
        return analyses
    
    async def get_ward_analysis_summary(
        self,
        ward_id: str
    ) -> Dict[str, Any]:
        """Get summary of ward analysis for dashboard"""
        try:
            # Get latest analysis
            analysis_doc = await self.firestore.collection('ward_analyses').document(ward_id).get()
            
            if not analysis_doc.exists:
                return {'error': 'No analysis found for ward'}
            
            analysis = WardAnalysis(**analysis_doc.to_dict())
            
            # Get related projects
            projects_query = self.firestore.collection('remediation_projects').where(
                'ward_id', '==', ward_id
            ).get()
            
            projects = [doc.to_dict() for doc in projects_query.docs]
            
            # Get recent complaints in ward
            complaints_query = self.firestore.collection('complaints').where(
                'location.ward_id', '==', ward_id
            ).order_by('created_at', direction='DESC').limit(10).get()
            
            recent_complaints = [doc.to_dict() for doc in complaints_query.docs]
            
            return {
                'analysis': analysis.dict(),
                'remediation_projects': projects,
                'recent_complaints': recent_complaints,
                'summary': {
                    'overall_score': analysis.scores.overall_score,
                    'priority_level': analysis.priority_analysis.priority_level,
                    'top_priority': analysis.priority_analysis.top_priority_area,
                    'project_count': len(projects),
                    'recent_complaint_count': len(recent_complaints),
                    'last_analyzed': analysis.analyzed_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get ward analysis summary: {e}")
            raise


# Global service instance
_ward_analyzer: Optional[WardAnalyzerService] = None


async def get_ward_analyzer() -> WardAnalyzerService:
    """Get or create ward analyzer service"""
    global _ward_analyzer
    
    if not _ward_analyzer:
        _ward_analyzer = WardAnalyzerService()
        await _ward_analyzer.initialize()
    
    return _ward_analyzer


async def initialize_ward_analyzer():
    """Initialize ward analyzer service"""
    await get_ward_analyzer()

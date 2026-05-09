"""Distance scoring using Google Distance Matrix API."""

from __future__ import annotations

import os
import time
from typing import Optional

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.housing_matcher.schemas import DistanceResult, HousingUnit
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class DistanceScoringError(Exception):
    """Raised when distance scoring fails."""


class DistanceScorer:
    """Calculate distances and travel times using Google Distance Matrix API."""

    def __init__(self):
        """Initialize distance scorer with API key."""
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        if not self.api_key:
            logger.warning("google_maps_api_key_missing", message="Distance scoring will use fallback")
        
        self.base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((requests.RequestException, TimeoutError)),
        reraise=True,
    )
    def calculate_distance(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> DistanceResult:
        """Calculate distance and duration between two points."""
        if not self.api_key:
            # Fallback to haversine distance calculation
            return self._calculate_haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        
        try:
            started = time.perf_counter()
            
            params = {
                "origins": f"{origin_lat},{origin_lng}",
                "destinations": f"{dest_lat},{dest_lng}",
                "mode": "driving",
                "key": self.api_key,
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.info("distance_api_latency", latency_ms=latency_ms)
            
            if data.get("status") != "OK":
                logger.warning("distance_api_error", status=data.get("status"))
                return self._calculate_haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
            
            rows = data.get("rows", [])
            if not rows or not rows[0].get("elements"):
                return self._calculate_haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
            
            element = rows[0]["elements"][0]
            
            if element.get("status") != "OK":
                return self._calculate_haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
            
            distance_meters = element.get("distance", {}).get("value", 0)
            duration_seconds = element.get("duration", {}).get("value", 0)
            
            distance_km = distance_meters / 1000.0
            duration_minutes = int(duration_seconds / 60)
            
            # Calculate accessibility score (inverse of distance, normalized)
            accessibility_score = self._calculate_accessibility_score(distance_km)
            
            return DistanceResult(
                distanceKm=round(distance_km, 2),
                durationMinutes=duration_minutes,
                accessibilityScore=round(accessibility_score, 2),
            )
        
        except Exception as exc:
            logger.error("distance_calculation_failed", error=str(exc))
            # Fallback to haversine
            return self._calculate_haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)

    def _calculate_haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> DistanceResult:
        """Calculate distance using Haversine formula (fallback)."""
        import math
        
        # Radius of Earth in kilometers
        R = 6371.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance_km = R * c
        
        # Estimate duration (assuming average speed of 30 km/h in city)
        duration_minutes = int((distance_km / 30.0) * 60)
        
        # Calculate accessibility score
        accessibility_score = self._calculate_accessibility_score(distance_km)
        
        logger.info("haversine_distance_calculated", distance_km=round(distance_km, 2))
        
        return DistanceResult(
            distanceKm=round(distance_km, 2),
            durationMinutes=duration_minutes,
            accessibilityScore=round(accessibility_score, 2),
        )

    def _calculate_accessibility_score(self, distance_km: float) -> float:
        """
        Calculate accessibility score based on distance.
        
        Scoring:
        - 0-5 km: 100 points (excellent)
        - 5-10 km: 80 points (good)
        - 10-20 km: 60 points (moderate)
        - 20-30 km: 40 points (far)
        - 30+ km: 20 points (very far)
        """
        if distance_km <= 5:
            return 100.0
        elif distance_km <= 10:
            return 80.0
        elif distance_km <= 20:
            return 60.0
        elif distance_km <= 30:
            return 40.0
        else:
            return 20.0

    def calculate_distances_batch(
        self,
        origin_lat: float,
        origin_lng: float,
        units: list[HousingUnit],
    ) -> dict[str, DistanceResult]:
        """Calculate distances for multiple units."""
        results = {}
        
        for unit in units:
            try:
                result = self.calculate_distance(
                    origin_lat,
                    origin_lng,
                    unit.latitude,
                    unit.longitude,
                )
                results[unit.unitId] = result
            except Exception as exc:
                logger.error(
                    "distance_calculation_failed_for_unit",
                    unit_id=unit.unitId,
                    error=str(exc),
                )
                # Use fallback with zero accessibility
                results[unit.unitId] = DistanceResult(
                    distanceKm=999.9,
                    durationMinutes=999,
                    accessibilityScore=0.0,
                )
        
        logger.info("distance_scoring_completed", units_scored=len(results))
        
        return results

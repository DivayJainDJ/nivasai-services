"""
Geolocation utilities for distance and proximity calculations.
"""

from typing import Tuple
import math


def calculate_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.

    Args:
        lat1, lon1: First coordinate (latitude, longitude)
        lat2, lon2: Second coordinate (latitude, longitude)

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def get_bounding_box(
    latitude: float, longitude: float, radius_km: float
) -> dict:
    """
    Get bounding box coordinates for a given radius.

    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius_km: Radius in kilometers

    Returns:
        Dictionary with north, south, east, west bounds
    """
    lat_delta = (radius_km / 111.0)  # 1 degree latitude ≈ 111 km
    lon_delta = lat_delta / math.cos(math.radians(latitude))

    return {
        "north": latitude + lat_delta,
        "south": latitude - lat_delta,
        "east": longitude + lon_delta,
        "west": longitude - lon_delta,
    }

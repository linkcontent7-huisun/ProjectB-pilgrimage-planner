"""Small geographic calculation helpers."""

from math import asin, cos, radians, sin, sqrt


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance between two WGS84 points in kilometres."""
    earth_radius_km = 6_371.0
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    a = (
        sin(delta_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lng / 2) ** 2
    )
    return earth_radius_km * 2 * asin(sqrt(a))

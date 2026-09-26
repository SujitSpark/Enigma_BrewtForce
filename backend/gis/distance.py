"""FEATURE 2 - distance calculation.

Baseline is the Haversine great-circle distance (straight-line / geodesic).
This is deterministic, dependency-free and runs offline. It is explicitly
labelled as ``haversine`` in every response so consumers know it is NOT a road
distance.
"""

from __future__ import annotations

import math
from typing import Union

from backend.gis.config import EARTH_RADIUS_KM
from backend.gis.coordinates import validate_coordinates
from backend.gis.schemas import Coordinate

DISTANCE_METHOD = "haversine"

PointLike = Union[Coordinate, tuple, list, dict]


def _as_coordinate(point: PointLike) -> Coordinate:
    if isinstance(point, Coordinate):
        return point
    if isinstance(point, dict):
        return validate_coordinates(point["latitude"], point["longitude"])
    if isinstance(point, (tuple, list)) and len(point) == 2:
        # Accept (lat, lon) ordered pairs.
        return validate_coordinates(point[0], point[1])
    raise TypeError(f"Unsupported point type: {type(point)!r}")


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    earth_radius_km: float = EARTH_RADIUS_KM,
) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    a = min(1.0, max(0.0, a))  # guard against floating point drift
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def distance_between(source: PointLike, destination: PointLike) -> float:
    """Distance in km between two points (Coordinate, dict, or (lat, lon))."""
    src = _as_coordinate(source)
    dst = _as_coordinate(destination)
    return haversine_distance_km(
        src.latitude, src.longitude, dst.latitude, dst.longitude
    )


def round_km(value: float, ndigits: int = 2) -> float:
    """Consistent rounding for API output."""
    return round(float(value), ndigits)

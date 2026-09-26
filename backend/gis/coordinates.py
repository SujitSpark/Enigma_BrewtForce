"""FEATURE 1 - coordinate resolution.

Resolution order (prototype-friendly, never hard-depends on a network):

1. Explicit latitude + longitude already supplied -> validate and use them.
2. Coordinates already stored in our industry dataset (by industry id).
3. Optional geocoding by city name via ``geopy``/Nominatim *only if installed*
   and explicitly enabled. The rest of the GIS module works without it.
"""

from __future__ import annotations

from typing import Optional

from backend.gis.schemas import Coordinate, Industry

# Optional dependency - imported lazily so the module never hard-fails.
try:  # pragma: no cover - depends on local environment
    from geopy.geocoders import Nominatim  # type: ignore

    GEOCODING_AVAILABLE = True
except Exception:  # pragma: no cover
    GEOCODING_AVAILABLE = False


class GeocodingUnavailableError(RuntimeError):
    """Raised when city-based geocoding was requested but is not available."""


def validate_coordinates(latitude: float, longitude: float) -> Coordinate:
    """Validate a lat/lon pair, raising ``ValueError`` on bad input."""
    if latitude is None or longitude is None:
        raise ValueError("latitude and longitude are required")
    if not (-90 <= latitude <= 90):
        raise ValueError(f"latitude out of range: {latitude}")
    if not (-180 <= longitude <= 180):
        raise ValueError(f"longitude out of range: {longitude}")
    return Coordinate(latitude=float(latitude), longitude=float(longitude))


def resolve_coordinate(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city: Optional[str] = None,
    allow_geocoding: bool = False,
) -> Coordinate:
    """Resolve a single location into a :class:`Coordinate`.

    Priority: explicit coordinates -> optional city geocoding.
    """
    if latitude is not None and longitude is not None:
        return validate_coordinates(latitude, longitude)

    if city and allow_geocoding:
        return geocode_city(city)

    if city:
        raise GeocodingUnavailableError(
            f"No coordinates supplied for city '{city}'. Provide latitude/longitude "
            "or set allow_geocoding=True (requires the optional 'geopy' package, and "
            "network access). The prototype prioritises stored coordinates."
        )
    raise ValueError("Could not resolve location: no coordinates or city supplied")


def coordinate_for_industry(industry: Industry) -> Coordinate:
    """Use the coordinates already stored on a dataset record."""
    return validate_coordinates(industry.latitude, industry.longitude)


def geocode_city(city: str, timeout: int = 10) -> Coordinate:  # pragma: no cover
    """Optional, network-dependent geocoding. Disabled unless geopy is installed."""
    if not GEOCODING_AVAILABLE:
        raise GeocodingUnavailableError(
            "geopy is not installed. Install it with 'pip install geopy' to enable "
            "city geocoding. The core GIS features do not need it."
        )
    geolocator = Nominatim(user_agent="enigma_brewtforce_gis_prototype")
    location = geolocator.geocode(city, timeout=timeout)
    if location is None:
        raise ValueError(f"Could not geocode city '{city}'")
    return validate_coordinates(location.latitude, location.longitude)

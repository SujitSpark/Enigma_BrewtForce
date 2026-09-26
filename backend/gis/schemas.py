"""Pydantic schemas for the GIS module.

These double as the API request/response models AND the integration contract
that Person 1 (matching) and Person 2 (impact) can rely on.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from backend.gis.config import DEFAULT_MAX_RADIUS_KM


class Coordinate(BaseModel):
    """A validated WGS84 latitude/longitude pair."""

    latitude: float = Field(..., ge=-90, le=90, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180, le=180, description="WGS84 longitude")


class Industry(BaseModel):
    """One prototype industry record from the dataset."""

    id: str
    name: str
    industry_type: str
    city: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    materials: List[str] = Field(default_factory=list)
    byproducts: List[str] = Field(default_factory=list)
    # Marked so nothing downstream mistakes demo data for real partners.
    data_note: str = "DEMO / PROTOTYPE DATA - not verified real industrial partners"

    @property
    def coordinate(self) -> Coordinate:
        return Coordinate(latitude=self.latitude, longitude=self.longitude)


class PointRef(BaseModel):
    """A location given either by coordinates or by a city name."""

    name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


# --------------------------------------------------------------------------- #
# FEATURE 2 - distance
# --------------------------------------------------------------------------- #
class DistanceRequest(BaseModel):
    source: Coordinate
    destination: Coordinate


class DistanceResponse(BaseModel):
    distance_km: float
    method: str = "haversine"


# --------------------------------------------------------------------------- #
# FEATURE 3 / 4 - nearby discovery
# --------------------------------------------------------------------------- #
class NearbyItem(BaseModel):
    industry_id: str
    name: str
    industry_type: str
    city: str
    latitude: float
    longitude: float
    distance_km: float
    within_radius: bool
    geographic_score: int
    feasibility: str

    @property
    def map_data(self):  # pragma: no cover - convenience only
        return {
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class NearbyResponse(BaseModel):
    source_id: str
    source_name: str
    radius_km: float
    count: int
    results: List[NearbyItem]


# --------------------------------------------------------------------------- #
# FEATURE 5 - evaluation
# --------------------------------------------------------------------------- #
class EvaluateRequest(BaseModel):
    source_id: str
    consumer_id: str
    max_radius_km: Optional[float] = Field(default=None, gt=0)


class EvaluateResponse(BaseModel):
    source: str
    consumer: str
    source_id: str
    consumer_id: str
    distance_km: float
    method: str = "haversine"
    max_radius_km: float
    within_radius: bool
    geographic_score: int
    feasibility: str
    map_data: dict


# --------------------------------------------------------------------------- #
# INTEGRATION CONTRACT - batch of candidates supplied by Person 1
# --------------------------------------------------------------------------- #
class OpportunitiesRequest(BaseModel):
    """Input contract: Person 1 supplies a source + candidate consumers."""

    source_id: str
    potential_consumers: List[str] = Field(default_factory=list)
    max_radius_km: float = Field(default=DEFAULT_MAX_RADIUS_KM, gt=0)


class Opportunity(BaseModel):
    """Output contract: consumed by Person 1 / Person 2 / frontend."""

    consumer_id: str
    consumer_name: str
    distance_km: float
    within_radius: bool
    geographic_score: int
    feasibility: str


class OpportunitiesResponse(BaseModel):
    source_id: str
    source_name: str
    max_radius_km: float
    opportunities: List[Opportunity]


class ErrorResponse(BaseModel):
    detail: str

"""Pydantic schemas for the GIS module.

These double as the API request/response models AND the integration contract
that Person 1 (matching) and Person 2 (impact) can rely on.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


# --------------------------------------------------------------------------- #
# evaluate-matches - flexible batch evaluation
#
# Accepts BOTH payload shapes used by the team:
#   A) compact:  source {id, name} + opportunities [{consumer_id, ...}]
#   B) rich:     source {id, name, ..., latitude, longitude, material, ...}
#                + matches [{id, name, ..., latitude, longitude}]
#
# Fields that look computed (distance_km, geographic_score, ...) are accepted
# for convenience but are ALWAYS recomputed server-side from real coordinates.
# --------------------------------------------------------------------------- #
class SourceRef(BaseModel):
    """Source industry reference; only some fields may be present."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    name: Optional[str] = None
    industry_type: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    material: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class OpportunityRef(BaseModel):
    """Compact candidate (Person 1's output shape).

    ``distance_km`` / ``geographic_score`` / ``feasibility`` / ``within_radius``
    are accepted but ignored - they are recomputed from coordinates.
    """

    model_config = ConfigDict(extra="ignore")

    consumer_id: Optional[str] = None
    consumer_name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    # Accepted but recomputed server-side:
    distance_km: Optional[float] = None
    within_radius: Optional[bool] = None
    geographic_score: Optional[int] = None
    feasibility: Optional[str] = None


class MatchRef(BaseModel):
    """Rich candidate (matching-module shape with explicit coordinates)."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    name: Optional[str] = None
    industry_type: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class EvaluateMatchesRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source: SourceRef
    matches: Optional[List[MatchRef]] = None
    opportunities: Optional[List[OpportunityRef]] = None
    # Echoed back untouched. Material/use compatibility is Person 1's scope.
    potential_uses: Optional[List[str]] = None
    max_radius_km: Optional[float] = Field(default=None, gt=0)


class MatchEvaluation(BaseModel):
    """Geographic verdict for ONE candidate match."""

    consumer_id: Optional[str] = None
    consumer_name: str
    industry_type: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # "payload" | "dataset" | "city:<Name>" | None (unresolved)
    coordinate_source: Optional[str] = None
    distance_km: Optional[float] = None
    within_radius: Optional[bool] = None
    geographic_score: Optional[int] = None
    feasibility: Optional[str] = None
    map_data: Optional[dict] = None
    status: str  # "ok" | "unresolved"
    detail: Optional[str] = None  # reason when unresolved


class EvaluateMatchesResponse(BaseModel):
    source: dict
    max_radius_km: float
    potential_uses: List[str] = Field(default_factory=list)
    count: int
    evaluated: int
    matches: List[MatchEvaluation]


class ErrorResponse(BaseModel):
    detail: str

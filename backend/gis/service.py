"""GIS service layer - the single entry point other modules should call.

Typical use::

    from backend.gis import get_default_service

    svc = get_default_service()
    svc.evaluate("IND001", "IND002", max_radius_km=50)
    svc.nearby_opportunities("IND001", ["IND002", "IND004"], max_radius_km=50)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from backend.gis.config import DEFAULT_SCORING_CONFIG, ScoringConfig
from backend.gis.coordinates import resolve_coordinate
from backend.gis.distance import distance_between
from backend.gis.feasibility import evaluate_distance
from backend.gis.nearby import find_nearby, to_nearby_item
from backend.gis.routes import RoutingProvider, StraightLineProvider, get_route
from backend.gis.schemas import Coordinate, Industry, NearbyItem, Opportunity


class IndustryNotFoundError(KeyError):
    """Raised when an industry id is not present in the dataset."""

    def __init__(self, industry_id: str) -> None:
        super().__init__(industry_id)
        self.industry_id = industry_id

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Industry '{self.industry_id}' was not found in the dataset"


# Default dataset lives next to this package, in backend/data/.
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "industries.json"


def load_industries(path: Optional[Path | str] = None) -> Dict[str, Industry]:
    """Load and validate the prototype industry dataset.

    Returns a dict keyed by industry id. Raises ``FileNotFoundError`` or
    ``ValueError`` (duplicate / malformed ids) on bad data.
    """
    data_path = Path(path) if path is not None else DEFAULT_DATA_PATH
    with open(data_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    records: Iterable[dict] = raw.get("industries", []) if isinstance(raw, dict) else raw

    industries: Dict[str, Industry] = {}
    for record in records:
        industry = Industry(**record)
        if industry.id in industries:
            raise ValueError(f"Duplicate industry id in dataset: {industry.id}")
        industries[industry.id] = industry
    if not industries:
        raise ValueError(f"No industries found in dataset: {data_path}")
    return industries


class GISService:
    """Pure-Python GIS operations over an in-memory industry dataset."""

    def __init__(
        self,
        industries: Dict[str, Industry],
        config: ScoringConfig = DEFAULT_SCORING_CONFIG,
        routing_provider: Optional[RoutingProvider] = None,
    ) -> None:
        if not industries:
            raise ValueError("GISService requires a non-empty industry dataset")
        self._industries = industries
        self.config = config
        self.routing_provider = routing_provider or StraightLineProvider()

    # ------------------------------------------------------------------ #
    # Lookups
    # ------------------------------------------------------------------ #
    @property
    def industries(self) -> Dict[str, Industry]:
        return self._industries

    def list_industries(self) -> List[Industry]:
        return list(self._industries.values())

    def get_industry(self, industry_id: str) -> Industry:
        try:
            return self._industries[industry_id]
        except KeyError:
            raise IndustryNotFoundError(industry_id) from None

    # ------------------------------------------------------------------ #
    # FEATURE 1 - coordinate resolution
    # ------------------------------------------------------------------ #
    def resolve_point(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        city: Optional[str] = None,
        allow_geocoding: bool = False,
    ) -> Coordinate:
        """Resolve arbitrary input into a Coordinate (geocoding is opt-in)."""
        if (latitude is None or longitude is None) and city:
            for industry in self._industries.values():
                if industry.city.lower() == city.strip().lower():
                    return industry.coordinate
        return resolve_coordinate(
            latitude=latitude,
            longitude=longitude,
            city=city,
            allow_geocoding=allow_geocoding,
        )

    # ------------------------------------------------------------------ #
    # FEATURE 2 - distance
    # ------------------------------------------------------------------ #
    def distance(
        self, source: Coordinate | dict, destination: Coordinate | dict
    ) -> dict:
        km = distance_between(source, destination)
        return {"distance_km": round(km, 2), "method": "haversine"}

    def distance_km(self, source_id: str, consumer_id: str) -> float:
        return distance_between(
            self.get_industry(source_id).coordinate,
            self.get_industry(consumer_id).coordinate,
        )

    # ------------------------------------------------------------------ #
    # FEATURE 3 / 4 - nearby discovery
    # ------------------------------------------------------------------ #
    def nearby(
        self,
        industry_id: str,
        radius_km: float,
        industry_type: Optional[str] = None,
        candidates: Optional[Sequence[str]] = None,
        include_outside_radius: bool = False,
    ) -> List[NearbyItem]:
        """Industries within ``radius_km`` of the given source industry."""
        source = self.get_industry(industry_id)
        pool = self.list_industries()
        if industry_type:
            pool = [i for i in pool if i.industry_type.lower() == industry_type.lower()]
        return find_nearby(
            source=source,
            industries=pool,
            radius_km=radius_km,
            config=self.config,
            candidates=candidates,
            include_outside_radius=include_outside_radius,
        )

    # ------------------------------------------------------------------ #
    # FEATURE 5 - evaluation
    # ------------------------------------------------------------------ #
    def evaluate(
        self, source_id: str, consumer_id: str, max_radius_km: Optional[float] = None
    ) -> dict:
        source = self.get_industry(source_id)
        consumer = self.get_industry(consumer_id)
        km = distance_between(source.coordinate, consumer.coordinate)
        effective = self.config.with_radius(max_radius_km)
        verdict = evaluate_distance(km, effective.max_radius_km, effective)
        return {
            "source": source.name,
            "consumer": consumer.name,
            "source_id": source.id,
            "consumer_id": consumer.id,
            "distance_km": verdict["distance_km"],
            "method": verdict["method"],
            "max_radius_km": verdict["max_radius_km"],
            "within_radius": verdict["within_radius"],
            "geographic_score": verdict["geographic_score"],
            "feasibility": verdict["feasibility"],
            "map_data": self.map_data(source, consumer, verdict["distance_km"]),
        }

    # ------------------------------------------------------------------ #
    # INTEGRATION CONTRACT - batch candidates from Person 1
    # ------------------------------------------------------------------ #
    def nearby_opportunities(
        self,
        source_id: str,
        potential_consumers: Sequence[str],
        max_radius_km: Optional[float] = None,
    ) -> List[Opportunity]:
        source = self.get_industry(source_id)
        effective = self.config.with_radius(max_radius_km)
        opportunities: List[Opportunity] = []
        for consumer_id in potential_consumers:
            consumer = self.get_industry(consumer_id)
            item = to_nearby_item(
                source, consumer, effective.max_radius_km, effective
            )
            opportunities.append(
                Opportunity(
                    consumer_id=item.industry_id,
                    consumer_name=item.name,
                    distance_km=item.distance_km,
                    within_radius=item.within_radius,
                    geographic_score=item.geographic_score,
                    feasibility=item.feasibility,
                )
            )
        opportunities.sort(key=lambda o: o.distance_km)
        return opportunities

    # ------------------------------------------------------------------ #
    # FEATURE 7 - map-ready output
    # ------------------------------------------------------------------ #
    @staticmethod
    def map_data(source: Industry, consumer: Industry, distance_km: float) -> dict:
        return {
            "source": {
                "name": source.name,
                "latitude": source.latitude,
                "longitude": source.longitude,
            },
            "consumer": {
                "name": consumer.name,
                "latitude": consumer.latitude,
                "longitude": consumer.longitude,
            },
            "distance_km": round(float(distance_km), 2),
            "method": "haversine",
        }

    # ------------------------------------------------------------------ #
    # FEATURE 6 - route (pluggable)
    # ------------------------------------------------------------------ #
    def route(self, source_id: str, consumer_id: str) -> dict:
        source = self.get_industry(source_id)
        consumer = self.get_industry(consumer_id)
        result = get_route(source.coordinate, consumer.coordinate, self.routing_provider)
        return result.as_dict()


_DEFAULT_SERVICE: Optional[GISService] = None


def get_default_service(reload: bool = False) -> GISService:
    """Return a cached GISService backed by the packaged dataset."""
    global _DEFAULT_SERVICE
    if _DEFAULT_SERVICE is None or reload:
        _DEFAULT_SERVICE = GISService(load_industries())
    return _DEFAULT_SERVICE


__all__ = [
    "GISService",
    "IndustryNotFoundError",
    "load_industries",
    "get_default_service",
    "DEFAULT_DATA_PATH",
]

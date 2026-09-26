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
from backend.gis.coordinates import resolve_coordinate, validate_coordinates
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

# Caps for the /gis/nearest endpoint.
MAX_NEAREST_LIMIT = 25
MAX_NEAREST_RADIUS_KM = 20000.0  # km, ~half the Earth's circumference


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
    # evaluate-matches - flexible batch evaluation (recomputes everything)
    # ------------------------------------------------------------------ #
    def _resolve_ref(
        self, *, ref_id, latitude, longitude, location
    ) -> tuple[Optional[Industry], Optional[Coordinate], str, Optional[str]]:
        """Resolution precedence: explicit coordinates -> dataset id -> city.

        When the caller supplies coordinates they are authoritative for this
        request; the dataset is the fallback when only an id is given. The
        origin is always reported via ``coordinate_source`` so nothing is
        silently substituted.
        """
        if latitude is not None and longitude is not None:
            try:
                return None, validate_coordinates(latitude, longitude), "payload", None
            except ValueError as exc:
                return None, None, "invalid", str(exc)
        if ref_id:
            try:
                industry = self.get_industry(ref_id)
                return industry, industry.coordinate, "dataset", None
            except IndustryNotFoundError:
                pass  # fall through to location matching
        if location:
            # Fallback: match a dataset record by city name (no network).
            for industry in self._industries.values():
                if industry.city.lower() == location.strip().lower():
                    return None, industry.coordinate, f"city:{industry.city}", None
            return None, None, "unresolved", f"No coordinates or dataset record for '{location}'"
        return None, None, "unresolved", "No id, coordinates or location supplied"

    def evaluate_matches(
        self,
        source,
        matches: Optional[Sequence] = None,
        opportunities: Optional[Sequence] = None,
        max_radius_km: Optional[float] = None,
        potential_uses: Optional[Sequence[str]] = None,
    ) -> dict:
        """Evaluate every candidate match against the source, geographically.

        Accepts the compact shape (``opportunities`` with pre-computed numbers)
        and the rich shape (``matches`` with explicit coordinates). All GIS
        values are recomputed here from real coordinates - supplied numbers in
        the payload are ignored, never echoed as results.
        """
        from backend.gis.schemas import MatchRef, OpportunityRef, SourceRef

        src = SourceRef(**source) if isinstance(source, dict) else source

        candidates: List[dict] = []
        for m in matches or []:
            m = MatchRef(**m) if isinstance(m, dict) else m
            candidates.append(
                {
                    "id": m.id,
                    "name": m.name,
                    "industry_type": m.industry_type,
                    "location": m.location or m.city,
                    "latitude": m.latitude,
                    "longitude": m.longitude,
                }
            )
        for o in opportunities or []:
            o = OpportunityRef(**o) if isinstance(o, dict) else o
            candidates.append(
                {
                    "id": o.consumer_id,
                    "name": o.consumer_name,
                    "industry_type": None,
                    "location": o.location,
                    "latitude": o.latitude,
                    "longitude": o.longitude,
                }
            )

        # --- resolve source ------------------------------------------------ #
        src_industry, src_coord, src_origin, src_error = self._resolve_ref(
            ref_id=src.id,
            latitude=src.latitude,
            longitude=src.longitude,
            location=src.location or src.city,
        )
        effective = self.config.with_radius(max_radius_km)

        source_out = {
            k: v for k, v in {
                "id": src.id,
                "name": src.name or (src_industry.name if src_industry else None),
                "industry_type": src.industry_type
                or (src_industry.industry_type if src_industry else None),
                "location": src.location or src.city
                or (src_industry.city if src_industry else None),
                "material": src.material,
                "quantity": src.quantity,
                "unit": src.unit,
            }.items() if v is not None
        }
        if src_coord is not None:
            source_out["latitude"] = src_coord.latitude
            source_out["longitude"] = src_coord.longitude
            source_out["coordinate_source"] = src_origin
        elif src_error:
            source_out["coordinate_source"] = "unresolved"
            source_out["warning"] = src_error

        # --- evaluate every candidate ------------------------------------- #
        evaluations: List[dict] = []
        for cand in candidates:
            # Metadata enrichment is independent of coordinate resolution.
            meta: Optional[Industry] = None
            if cand["id"]:
                try:
                    meta = self.get_industry(cand["id"])
                except IndustryNotFoundError:
                    meta = None
            ind, coord, origin, error = self._resolve_ref(
                ref_id=cand["id"],
                latitude=cand["latitude"],
                longitude=cand["longitude"],
                location=cand["location"],
            )
            entry: dict = {
                "consumer_id": cand["id"] or (meta.id if meta else None),
                "consumer_name": cand["name"]
                or (meta.name if meta else None)
                or "Unknown",
                "industry_type": cand["industry_type"]
                or (meta.industry_type if meta else None),
                "location": cand["location"] or (meta.city if meta else None),
            }
            if coord is None:
                entry.update(
                    {
                        "coordinate_source": origin,
                        "status": "unresolved",
                        "detail": error or "Could not resolve coordinates",
                        "distance_km": None,
                        "within_radius": None,
                        "geographic_score": None,
                        "feasibility": None,
                        "map_data": None,
                    }
                )
                evaluations.append(entry)
                continue

            if src_coord is None:
                # Source itself could not be resolved: nothing to measure from.
                entry.update(
                    {
                        "latitude": coord.latitude,
                        "longitude": coord.longitude,
                        "coordinate_source": origin,
                        "status": "unresolved",
                        "detail": "Source coordinates could not be resolved",
                        "distance_km": None,
                        "within_radius": None,
                        "geographic_score": None,
                        "feasibility": None,
                        "map_data": None,
                    }
                )
                evaluations.append(entry)
                continue

            km = distance_between(src_coord, coord)
            verdict = evaluate_distance(km, effective.max_radius_km, effective)
            md = {
                "source": {
                    "name": source_out.get("name"),
                    "latitude": src_coord.latitude,
                    "longitude": src_coord.longitude,
                },
                "consumer": {
                    "name": entry["consumer_name"],
                    "latitude": coord.latitude,
                    "longitude": coord.longitude,
                },
                "distance_km": verdict["distance_km"],
                "method": "haversine",
            }
            entry.update(
                {
                    "latitude": coord.latitude,
                    "longitude": coord.longitude,
                    "coordinate_source": origin,
                    "distance_km": verdict["distance_km"],
                    "within_radius": verdict["within_radius"],
                    "geographic_score": verdict["geographic_score"],
                    "feasibility": verdict["feasibility"],
                    "map_data": md,
                    "status": "ok",
                    "detail": None,
                }
            )
            evaluations.append(entry)

        # Nearest first; unresolved entries keep input order at the end.
        evaluations.sort(
            key=lambda e: (
                e["distance_km"] is None,
                e["distance_km"] if e["distance_km"] is not None else 0.0,
            )
        )

        evaluated = sum(1 for e in evaluations if e["status"] == "ok")
        return {
            "source": source_out,
            "max_radius_km": effective.max_radius_km,
            "potential_uses": list(potential_uses or []),
            "count": len(evaluations),
            "evaluated": evaluated,
            "matches": evaluations,
        }

    # ------------------------------------------------------------------ #
    # Dataset statistics (purely geographic/data-oriented)
    # ------------------------------------------------------------------ #
    def summary(self) -> dict:
        """GIS-level statistics over the loaded dataset.

        Purely geographic/data-oriented: counts, distances, coverage. It does
        NOT compute environmental impact, CO2 savings, or scheme eligibility.
        """
        industries = self.list_industries()
        total = len(industries)
        pairs = total * (total - 1) // 2

        # Pairwise distances (N is small for the prototype, O(N^2) is fine).
        coords = [i.coordinate for i in industries]
        distances = [
            distance_between(coords[a], coords[b])
            for a in range(total)
            for b in range(a + 1, total)
        ]
        avg = round(sum(distances) / len(distances), 2) if distances else 0.0
        max_pair = max(distances) if distances else 0.0

        by_type: Dict[str, int] = {}
        for i in industries:
            by_type[i.industry_type] = by_type.get(i.industry_type, 0) + 1

        cities = sorted({i.city for i in industries})

        return {
            "total_industries": total,
            "industries_with_coordinates": sum(
                1
                for i in industries
                if i.latitude is not None and i.longitude is not None
            ),
            "total_possible_connections": pairs,
            "average_distance_km": avg,
            "max_pairwise_distance_km": round(max_pair, 2),
            "industries_by_type": dict(sorted(by_type.items())),
            "cities": cities,
            "cities_covered": len(cities),
        }

    def nearest(self, industry_id: str, limit: int = 5) -> dict:
        """Nearest industries to a given one, sorted by distance ascending.

        The source industry itself is always excluded.
        """
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if limit > MAX_NEAREST_LIMIT:
            raise ValueError(f"limit must be <= {MAX_NEAREST_LIMIT}")

        source = self.get_industry(industry_id)
        items = find_nearby(
            source=source,
            industries=self.list_industries(),
            radius_km=MAX_NEAREST_RADIUS_KM,  # effectively unbounded
            config=self.config,
            include_outside_radius=True,
        )
        nearest = items[:limit]
        return {
            "source": {"id": source.id, "name": source.name},
            "count": len(nearest),
            "limit": limit,
            "nearest_industries": [
                {
                    "id": n.industry_id,
                    "name": n.name,
                    "industry_type": n.industry_type,
                    "city": n.city,
                    "latitude": n.latitude,
                    "longitude": n.longitude,
                    "distance_km": n.distance_km,
                    "geographic_score": n.geographic_score,
                    "feasibility": n.feasibility,
                }
                for n in nearest
            ],
        }

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

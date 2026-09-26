"""FEATURE 3 / 4 - radius filtering and nearby-industry discovery.

No material compatibility is decided here. Person 1 decides *which* industries
are relevant; GIS answers *where* they are and how feasible the geography is.
Inputs may be either the full dataset (radius scan) or an explicit candidate
list supplied by Person 1.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from backend.gis.config import DEFAULT_SCORING_CONFIG, ScoringConfig
from backend.gis.distance import distance_between
from backend.gis.feasibility import (
    feasibility_band,
    geographic_score,
    is_within_radius,
)
from backend.gis.schemas import Industry, NearbyItem


def to_nearby_item(
    source: Industry,
    candidate: Industry,
    max_radius_km: float,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> NearbyItem:
    """Build a map-ready :class:`NearbyItem` for one source/candidate pair."""
    dist = distance_between(source.coordinate, candidate.coordinate)
    return NearbyItem(
        industry_id=candidate.id,
        name=candidate.name,
        industry_type=candidate.industry_type,
        city=candidate.city,
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        distance_km=round(dist, 2),
        within_radius=is_within_radius(dist, max_radius_km),
        geographic_score=geographic_score(dist, config),
        feasibility=feasibility_band(dist, config),
    )


def find_nearby(
    source: Industry,
    industries: Iterable[Industry],
    radius_km: float,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
    candidates: Optional[Sequence[str]] = None,
    include_outside_radius: bool = False,
) -> List[NearbyItem]:
    """Return industries within ``radius_km`` of ``source``, nearest first.

    Parameters
    ----------
    source:
        The source industry record.
    industries:
        The pool of industries to scan.
    radius_km:
        Maximum radius in km (inclusive).
    candidates:
        Optional whitelist of industry ids (typically supplied by Person 1).
    include_outside_radius:
        When True, also return items outside the radius (flagged as such) so the
        caller can show a "just beyond range" fallback list.
    """
    if radius_km <= 0:
        raise ValueError("radius_km must be > 0")
    effective = config.with_radius(radius_km)
    allowed = set(candidates) if candidates is not None else None

    items: List[NearbyItem] = []
    for candidate in industries:
        if candidate.id == source.id:
            continue
        if allowed is not None and candidate.id not in allowed:
            continue
        item = to_nearby_item(source, candidate, radius_km, effective)
        if include_outside_radius or item.within_radius:
            items.append(item)

    items.sort(key=lambda i: i.distance_km)
    return items

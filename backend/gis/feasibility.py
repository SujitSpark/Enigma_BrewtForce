"""FEATURE 5 - transparent, configurable geographic feasibility score.

Two independent, explainable outputs:

* ``geographic_score`` (0-100): piecewise-linear interpolation over the
  configurable anchors in :mod:`backend.gis.config`. 0 km -> 100, decaying with
  distance, clamped to [0, 100].
* ``feasibility``: a coarse human label from the configurable distance bands
  (VERY_HIGH / HIGH / MODERATE / LOW).

There is NO material-compatibility logic here - that belongs to Person 1.
These thresholds are prototype heuristics, not a scientific or government
standard.
"""

from __future__ import annotations

from typing import Iterable, Sequence, Tuple

from backend.gis.config import DEFAULT_SCORING_CONFIG, ScoringConfig


def geographic_score(
    distance_km: float, config: ScoringConfig = DEFAULT_SCORING_CONFIG
) -> int:
    """Piecewise-linear 0-100 score. Closer means higher."""
    if distance_km < 0:
        raise ValueError("distance_km must be >= 0")

    anchors: Sequence[Tuple[float, int]] = config.score_anchors
    if distance_km <= anchors[0][0]:
        return int(anchors[0][1])
    if distance_km >= anchors[-1][0]:
        return int(anchors[-1][1])

    for (d0, s0), (d1, s1) in zip(anchors, anchors[1:]):
        if d0 <= distance_km <= d1:
            span = d1 - d0
            if span == 0:
                return int(s1)
            ratio = (distance_km - d0) / span
            return int(round(s0 + ratio * (s1 - s0)))

    return int(anchors[-1][1])


def feasibility_band(
    distance_km: float, config: ScoringConfig = DEFAULT_SCORING_CONFIG
) -> str:
    """Coarse feasibility label for a distance."""
    if distance_km < 0:
        raise ValueError("distance_km must be >= 0")
    for max_km, label in config.bands:
        if distance_km <= max_km:
            return label
    return config.bands[-1][1]


def is_within_radius(distance_km: float, max_radius_km: float) -> bool:
    """Boundary is inclusive: distance == radius counts as inside."""
    return distance_km <= max_radius_km


def evaluate_distance(
    distance_km: float,
    max_radius_km: float,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> dict:
    """Full feasibility verdict for one source/consumer pair."""
    effective = config.with_radius(max_radius_km)
    return {
        "distance_km": round(float(distance_km), 2),
        "max_radius_km": float(max_radius_km),
        "within_radius": is_within_radius(distance_km, max_radius_km),
        "geographic_score": geographic_score(distance_km, effective),
        "feasibility": feasibility_band(distance_km, effective),
        "method": "haversine",
    }


def scan_distances(
    distances: Iterable[Tuple[str, float]],
) -> list[Tuple[str, float]]:
    """Helper: sort ``(id, distance_km)`` pairs ascending by distance."""
    return sorted(distances, key=lambda item: item[1])

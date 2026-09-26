"""Configurable thresholds for the GIS module.

IMPORTANT: The bands and score anchors below are PROTOTYPE HEURISTICS chosen for
demo purposes. They are NOT scientifically derived, and they are NOT a
government-defined standard. They are exposed here (and overridable per request
through the API) precisely so they can be tuned without touching logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

# Default search radius when a request does not supply one (km).
DEFAULT_MAX_RADIUS_KM: float = 50.0

# Human-readable feasibility labels, ordered by *maximum* distance in km.
# (max_km_inclusive, label) - the last entry acts as the fallback band.
DEFAULT_FEASIBILITY_BANDS: List[Tuple[float, str]] = [
    (25.0, "VERY_HIGH"),
    (50.0, "HIGH"),
    (100.0, "MODERATE"),
    (float("inf"), "LOW"),
]

# Transparent piecewise-linear score anchors: (distance_km, score_0_to_100).
# The score is linearly interpolated between anchors and clamped to [0, 100].
DEFAULT_SCORE_ANCHORS: List[Tuple[float, int]] = [
    (0.0, 100),
    (25.0, 90),
    (50.0, 70),
    (100.0, 40),
    (250.0, 10),
    (500.0, 0),
]

# Earth mean radius in km (used by the Haversine implementation).
EARTH_RADIUS_KM: float = 6371.0088


@dataclass(frozen=True)
class ScoringConfig:
    """Bundle of tunable knobs for geographic feasibility."""

    max_radius_km: float = DEFAULT_MAX_RADIUS_KM
    bands: List[Tuple[float, str]] = field(
        default_factory=lambda: list(DEFAULT_FEASIBILITY_BANDS)
    )
    score_anchors: List[Tuple[float, int]] = field(
        default_factory=lambda: list(DEFAULT_SCORE_ANCHORS)
    )

    def with_radius(self, max_radius_km: float | None) -> "ScoringConfig":
        """Return a copy with an overridden radius (falls back to self)."""
        if max_radius_km is None:
            return self
        if max_radius_km <= 0:
            raise ValueError("max_radius_km must be > 0")
        return ScoringConfig(
            max_radius_km=float(max_radius_km),
            bands=self.bands,
            score_anchors=self.score_anchors,
        )


DEFAULT_SCORING_CONFIG = ScoringConfig()

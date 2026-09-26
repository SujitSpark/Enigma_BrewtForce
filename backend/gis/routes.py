"""FEATURE 6 - route / road-distance support (pluggable, optional).

Design goals:
* The module NEVER depends on a paid routing API.
* Baseline is straight-line Haversine, always available, clearly labelled.
* A road-routing provider can be plugged in later (e.g. the public OSRM demo
  server, or a self-hosted OSRM/GraphHopper) by implementing ``RoutingProvider``.

The OSRM provider below is OFF by default and network-dependent. It uses only
the standard library (urllib) so it adds no dependency.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Optional

from backend.gis.distance import distance_between
from backend.gis.schemas import Coordinate

DEFAULT_OSRM_BASE_URL = "http://router.project-osrm.org"


@dataclass
class RouteResult:
    distance_km: float
    duration_minutes: Optional[float]
    provider: str  # "haversine" | "osrm" | ...

    def as_dict(self) -> dict:
        return {
            "distance_km": round(self.distance_km, 2),
            "duration_minutes": (
                round(self.duration_minutes, 1)
                if self.duration_minutes is not None
                else None
            ),
            "provider": self.provider,
        }


class RoutingProvider:
    """Interface for pluggable route providers."""

    name = "base"

    def route(self, source: Coordinate, destination: Coordinate) -> RouteResult:
        raise NotImplementedError


class StraightLineProvider(RoutingProvider):
    """Default provider: great-circle distance, always available offline."""

    name = "haversine"

    def route(self, source: Coordinate, destination: Coordinate) -> RouteResult:
        return RouteResult(
            distance_km=distance_between(source, destination),
            duration_minutes=None,
            provider=self.name,
        )


class OSRMProvider(RoutingProvider):
    """Optional road routing via a public/self-hosted OSRM server.

    Disabled by default. Enable explicitly (and only when network is available):

        provider = OSRMProvider(enabled=True)
    """

    name = "osrm"

    def __init__(
        self, base_url: str = DEFAULT_OSRM_BASE_URL, enabled: bool = False, timeout: int = 8
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.enabled = enabled
        self.timeout = timeout

    def route(self, source: Coordinate, destination: Coordinate) -> RouteResult:
        if not self.enabled:
            raise RuntimeError(
                "OSRM road routing is disabled. Set enabled=True to use it; the "
                "prototype defaults to straight-line distance."
            )
        coords = (
            f"{source.longitude},{source.latitude};"
            f"{destination.longitude},{destination.latitude}"
        )
        url = f"{self.base_url}/route/v1/driving/{coords}?overview=false"
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        route = (payload.get("routes") or [{}])[0]
        return RouteResult(
            distance_km=route.get("distance", 0.0) / 1000.0,
            duration_minutes=route.get("duration", 0.0) / 60.0,
            provider=self.name,
        )


def get_route(
    source: Coordinate,
    destination: Coordinate,
    provider: Optional[RoutingProvider] = None,
) -> RouteResult:
    """Route using the given provider, falling back to straight-line on failure."""
    provider = provider or StraightLineProvider()
    try:
        return provider.route(source, destination)
    except Exception:
        # Never let an external/hard dependency break the GIS module.
        return StraightLineProvider().route(source, destination)

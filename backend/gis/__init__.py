"""GIS / Location Intelligence module (Person 3).

Public surface for other modules:

    from backend.gis import GISService, get_default_service, ScoringConfig

    svc = get_default_service()
    svc.evaluate(source_id="IND001", consumer_id="IND005", max_radius_km=50)

Everything here is pure Python + FastAPI/Pydantic. No ML, no GPU, no paid APIs.
Routes/road-distance is pluggable (see ``routes.py``) but defaults to
geodesic (straight-line) distance so the prototype never depends on a network.
"""

from backend.gis.config import ScoringConfig, DEFAULT_SCORING_CONFIG
from backend.gis.service import GISService, get_default_service, load_industries

__all__ = [
    "ScoringConfig",
    "DEFAULT_SCORING_CONFIG",
    "GISService",
    "get_default_service",
    "load_industries",
]

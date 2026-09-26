"""FastAPI routes for the GIS / Location Intelligence module.

Base prefix (set in ``main.py``): ``/gis``
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.gis.config import DEFAULT_MAX_RADIUS_KM
from backend.gis.routes import OSRMProvider, StraightLineProvider
from backend.gis.schemas import (
    DistanceRequest,
    DistanceResponse,
    ErrorResponse,
    EvaluateMatchesRequest,
    EvaluateMatchesResponse,
    EvaluateRequest,
    EvaluateResponse,
    Industry,
    NearbyItem,
    NearbyResponse,
    NearestResponse,
    OpportunitiesRequest,
    OpportunitiesResponse,
    SummaryResponse,
)
from backend.gis.service import GISService, IndustryNotFoundError, get_default_service
from backend.gis.service import MAX_NEAREST_LIMIT

router = APIRouter(tags=["GIS / Location Intelligence"])


def get_service() -> GISService:
    """Dependency hook - overridable in tests via ``app.dependency_overrides``."""
    return get_default_service()


def _not_found(exc: IndustryNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/health", summary="GIS module health check")
def health() -> dict:
    svc = get_service()
    return {
        "status": "ok",
        "module": "GIS / Location Intelligence",
        "industries_loaded": len(svc.industries),
        "default_radius_km": DEFAULT_MAX_RADIUS_KM,
        "distance_method": "haversine",
    }


@router.get("/industries", response_model=List[Industry], summary="List all industries")
def list_industries() -> List[Industry]:
    return get_service().list_industries()


# --------------------------------------------------------------------------- #
# FEATURE 1 - coordinate resolution
# --------------------------------------------------------------------------- #
@router.get(
    "/industry/{industry_id}",
    response_model=Industry,
    responses={404: {"model": ErrorResponse}},
    summary="Get one industry with its coordinates",
)
def get_industry(industry_id: str) -> Industry:
    try:
        return get_service().get_industry(industry_id)
    except IndustryNotFoundError as exc:
        raise _not_found(exc)


# --------------------------------------------------------------------------- #
# Dataset summary (purely geographic/data-oriented)
# --------------------------------------------------------------------------- #
@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="GIS-level dataset statistics (counts, distances, coverage)",
)
def get_summary() -> SummaryResponse:
    return SummaryResponse(**get_service().summary())


# --------------------------------------------------------------------------- #
# Nearest industries
# --------------------------------------------------------------------------- #
@router.get(
    "/nearest/{industry_id}",
    response_model=NearestResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Nearest industries to a given industry, sorted by distance",
)
def get_nearest(
    industry_id: str,
    limit: int = Query(5, ge=1, le=MAX_NEAREST_LIMIT, description="Max results (1-25)"),
) -> NearestResponse:
    try:
        return NearestResponse(**get_service().nearest(industry_id, limit))
    except IndustryNotFoundError as exc:
        raise _not_found(exc)


# --------------------------------------------------------------------------- #
# FEATURE 3 / 4 - nearby discovery (two equivalent forms)
# --------------------------------------------------------------------------- #
@router.get(
    "/nearby/{industry_id}",
    response_model=NearbyResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Nearby industries within a radius",
)
def nearby_by_path(
    industry_id: str,
    radius_km: float = Query(DEFAULT_MAX_RADIUS_KM, gt=0, le=20000),
    industry_type: Optional[str] = Query(None, description="Optional type filter"),
    include_outside_radius: bool = Query(
        False, description="Also return out-of-radius industries (flagged)"
    ),
) -> NearbyResponse:
    return _nearby(industry_id, radius_km, industry_type, include_outside_radius)


@router.get(
    "/nearby",
    response_model=NearbyResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Nearby industries within a radius (query-parameter form)",
)
def nearby_by_query(
    industry_id: str = Query(..., description="Source industry id, e.g. IND001"),
    radius_km: float = Query(DEFAULT_MAX_RADIUS_KM, gt=0, le=20000),
    industry_type: Optional[str] = Query(None),
    include_outside_radius: bool = Query(False),
) -> NearbyResponse:
    return _nearby(industry_id, radius_km, industry_type, include_outside_radius)


def _nearby(
    industry_id: str,
    radius_km: float,
    industry_type: Optional[str],
    include_outside_radius: bool,
) -> NearbyResponse:
    svc = get_service()
    try:
        source = svc.get_industry(industry_id)
    except IndustryNotFoundError as exc:
        raise _not_found(exc)
    results = svc.nearby(
        industry_id,
        radius_km,
        industry_type=industry_type,
        include_outside_radius=include_outside_radius,
    )
    return NearbyResponse(
        source_id=source.id,
        source_name=source.name,
        radius_km=radius_km,
        count=len(results),
        results=results,
    )


# --------------------------------------------------------------------------- #
# FEATURE 2 - distance
# --------------------------------------------------------------------------- #
@router.post(
    "/distance",
    response_model=DistanceResponse,
    summary="Distance between two coordinate pairs (Haversine, km)",
)
def post_distance(payload: DistanceRequest) -> DistanceResponse:
    result = get_service().distance(payload.source, payload.destination)
    return DistanceResponse(**result)


# --------------------------------------------------------------------------- #
# FEATURE 5 - evaluation
# --------------------------------------------------------------------------- #
@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Full geographic feasibility between two industries",
)
def post_evaluate(payload: EvaluateRequest) -> EvaluateResponse:
    try:
        result = get_service().evaluate(
            payload.source_id, payload.consumer_id, payload.max_radius_km
        )
    except IndustryNotFoundError as exc:
        raise _not_found(exc)
    return EvaluateResponse(**result)


# --------------------------------------------------------------------------- #
# evaluate-matches - flexible batch evaluation for the matching module
# --------------------------------------------------------------------------- #
@router.post(
    "/evaluate-matches",
    response_model=EvaluateMatchesResponse,
    responses={404: {"model": ErrorResponse}},
    summary=(
        "Evaluate a batch of candidate matches (accepts both the compact "
        "'opportunities' shape and the rich 'matches' shape); all GIS values "
        "are recomputed from real coordinates"
    ),
)
def post_evaluate_matches(payload: EvaluateMatchesRequest) -> EvaluateMatchesResponse:
    svc = get_service()
    if payload.source is None or not (payload.source.id or payload.source.latitude is not None or payload.source.location):
        raise HTTPException(status_code=422, detail="source must include an id, coordinates or a location")
    result = svc.evaluate_matches(
        source=payload.source,
        matches=payload.matches,
        opportunities=payload.opportunities,
        max_radius_km=payload.max_radius_km,
        potential_uses=payload.potential_uses,
    )
    return EvaluateMatchesResponse(**result)


# --------------------------------------------------------------------------- #
# INTEGRATION CONTRACT - batch from Person 1 (matching)
# --------------------------------------------------------------------------- #
@router.post(
    "/opportunities",
    response_model=OpportunitiesResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Evaluate a list of candidate consumers supplied by the matching module",
)
def post_opportunities(payload: OpportunitiesRequest) -> OpportunitiesResponse:
    svc = get_service()
    try:
        source = svc.get_industry(payload.source_id)
        opportunities = svc.nearby_opportunities(
            payload.source_id, payload.potential_consumers, payload.max_radius_km
        )
    except IndustryNotFoundError as exc:
        raise _not_found(exc)
    return OpportunitiesResponse(
        source_id=source.id,
        source_name=source.name,
        max_radius_km=payload.max_radius_km,
        opportunities=opportunities,
    )


# --------------------------------------------------------------------------- #
# FEATURE 7 - map-ready output
# --------------------------------------------------------------------------- #
@router.get(
    "/map/{source_id}/{consumer_id}",
    responses={404: {"model": ErrorResponse}},
    summary="Map-ready JSON for a source/consumer pair (for Leaflet etc.)",
)
def get_map_data(source_id: str, consumer_id: str) -> dict:
    svc = get_service()
    try:
        return svc.evaluate(source_id, consumer_id)["map_data"]
    except IndustryNotFoundError as exc:
        raise _not_found(exc)


# --------------------------------------------------------------------------- #
# FEATURE 6 - route information (pluggable; straight-line by default)
# --------------------------------------------------------------------------- #
@router.get(
    "/route/{source_id}/{consumer_id}",
    responses={404: {"model": ErrorResponse}},
    summary="Route/distance information (straight-line by default, OSRM optional)",
)
def get_route_info(
    source_id: str,
    consumer_id: str,
    provider: str = Query(
        "straight_line",
        description="'straight_line' (default, offline) or 'osrm' (optional, network)",
    ),
) -> dict:
    svc = get_service()
    if provider == "osrm":
        svc = GISService(svc.industries, svc.config, routing_provider=OSRMProvider(enabled=True))
    elif provider == "straight_line":
        svc = GISService(svc.industries, svc.config, routing_provider=StraightLineProvider())
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    try:
        return svc.route(source_id, consumer_id)
    except IndustryNotFoundError as exc:
        raise _not_found(exc)

"""Tests: FastAPI endpoints (uses fastapi.testclient, requires httpx)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    r = client.get("/gis/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root():
    assert client.get("/").status_code == 200


def test_get_industry_and_404():
    ok = client.get("/gis/industry/IND001")
    assert ok.status_code == 200
    assert ok.json()["id"] == "IND001"

    missing = client.get("/gis/industry/IND999")
    assert missing.status_code == 404


def test_nearby_both_forms():
    a = client.get("/gis/nearby/IND001", params={"radius_km": 50})
    b = client.get("/gis/nearby", params={"industry_id": "IND001", "radius_km": 50})
    assert a.status_code == b.status_code == 200
    assert a.json()["count"] == b.json()["count"]
    assert a.json()["radius_km"] == 50


def test_distance_endpoint():
    payload = {
        "source": {"latitude": 18.5204, "longitude": 73.8567},
        "destination": {"latitude": 18.6000, "longitude": 73.8000},
    }
    r = client.post("/gis/distance", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["distance_km"] > 0
    assert body["method"] == "haversine"


def test_distance_rejects_invalid_coordinates():
    payload = {
        "source": {"latitude": 200, "longitude": 73.8},
        "destination": {"latitude": 18.6, "longitude": 73.8},
    }
    assert client.post("/gis/distance", json=payload).status_code == 422


def test_evaluate_endpoint():
    r = client.post(
        "/gis/evaluate",
        json={"source_id": "IND001", "consumer_id": "IND002", "max_radius_km": 50},
    )
    assert r.status_code == 200
    body = r.json()
    for key in (
        "distance_km",
        "within_radius",
        "geographic_score",
        "feasibility",
        "map_data",
    ):
        assert key in body


def test_opportunities_endpoint_contract():
    r = client.post(
        "/gis/opportunities",
        json={
            "source_id": "IND001",
            "potential_consumers": ["IND002", "IND004", "IND014"],
            "max_radius_km": 50,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["opportunities"]) == 3
    assert set(body["opportunities"][0]) == {
        "consumer_id",
        "consumer_name",
        "distance_km",
        "within_radius",
        "geographic_score",
        "feasibility",
    }


def test_map_endpoint():
    r = client.get("/gis/map/IND001/IND002")
    assert r.status_code == 200
    assert {"source", "consumer", "distance_km"} <= set(r.json())


def test_route_endpoint():
    r = client.get("/gis/route/IND001/IND002")
    assert r.status_code == 200
    assert r.json()["provider"] == "haversine"


def test_openapi_docs_available():
    assert client.get("/openapi.json").status_code == 200

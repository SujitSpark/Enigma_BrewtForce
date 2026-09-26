"""Tests: /gis/summary, /gis/nearest, expanded dataset, radius demonstration.

Also acts as the regression guard for the evaluate-matches contract.
"""

import pytest
from fastapi.testclient import TestClient

from backend.gis.service import get_default_service, load_industries
from backend.main import app

client = TestClient(app)
SVC = get_default_service()
INDUSTRIES = load_industries()


# --------------------------------------------------------------------------- #
# SUMMARY
# --------------------------------------------------------------------------- #
def test_summary_returns_200_and_core_fields():
    r = client.get("/gis/summary")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "total_industries",
        "industries_with_coordinates",
        "total_possible_connections",
        "average_distance_km",
    ):
        assert key in body


def test_summary_counts_are_correct():
    body = client.get("/gis/summary").json()
    n = len(INDUSTRIES)
    assert body["total_industries"] == n
    assert body["industries_with_coordinates"] == n  # every record has coords
    assert body["total_possible_connections"] == n * (n - 1) // 2


def test_summary_average_distance_matches_bruteforce():
    body = client.get("/gis/summary").json()
    inds = list(INDUSTRIES.values())
    coords = [(i.latitude, i.longitude) for i in inds]
    from backend.gis.distance import haversine_distance_km

    dists = [
        haversine_distance_km(*coords[a], *coords[b])
        for a in range(len(coords))
        for b in range(a + 1, len(coords))
    ]
    assert body["average_distance_km"] == pytest.approx(
        sum(dists) / len(dists), abs=0.01
    )
    assert body["average_distance_km"] > 0


def test_summary_is_purely_geographic():
    body = client.get("/gis/summary").json()
    forbidden = ("co2", "carbon", "emission", "scheme", "subsidy", "impact")
    text = str(body).lower()
    assert not any(word in text for word in forbidden)


def test_summary_breakdowns_present():
    body = client.get("/gis/summary").json()
    assert body["industries_by_type"]
    assert sum(body["industries_by_type"].values()) == len(INDUSTRIES)
    assert body["cities_covered"] == len(body["cities"])
    assert body["cities_covered"] >= 15  # spread across Maharashtra


# --------------------------------------------------------------------------- #
# NEAREST
# --------------------------------------------------------------------------- #
def test_nearest_returns_200_and_excludes_source():
    r = client.get("/gis/nearest/IND001")
    assert r.status_code == 200
    body = r.json()
    assert body["source"]["id"] == "IND001"
    ids = [n["id"] for n in body["nearest_industries"]]
    assert "IND001" not in ids
    assert ids  # non-empty


def test_nearest_sorted_ascending_by_distance():
    body = client.get("/gis/nearest/IND001").json()
    dists = [n["distance_km"] for n in body["nearest_industries"]]
    assert dists == sorted(dists)


def test_nearest_distances_match_service():
    body = client.get("/gis/nearest/IND001").json()
    for n in body["nearest_industries"]:
        expected = round(SVC.distance_km("IND001", n["id"]), 2)
        assert n["distance_km"] == expected


def test_nearest_limit_respected():
    body = client.get("/gis/nearest/IND001", params={"limit": 3}).json()
    assert body["count"] == 3
    assert body["limit"] == 3
    assert len(body["nearest_industries"]) == 3


def test_nearest_default_limit_is_5():
    body = client.get("/gis/nearest/IND001").json()
    assert body["limit"] == 5
    assert body["count"] == min(5, len(INDUSTRIES) - 1)


def test_nearest_invalid_limit_rejected():
    for params in ({"limit": 0}, {"limit": -2}, {"limit": 26}, {"limit": 999}):
        r = client.get("/gis/nearest/IND001", params=params)
        assert r.status_code == 422, params


def test_nearest_unknown_industry_404():
    r = client.get("/gis/nearest/IND999")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


# --------------------------------------------------------------------------- #
# DATASET integrity
# --------------------------------------------------------------------------- #
def test_dataset_ids_unique():
    ids = [i.id for i in INDUSTRIES.values()]
    assert len(ids) == len(set(ids))


def test_dataset_ids_stable_and_predictable():
    ids = sorted(INDUSTRIES)
    assert ids[0] == "IND001"
    assert all(i.startswith("IND") for i in ids)
    # IND001..IND015 are the original stable records.
    for original in [f"IND{i:03d}" for i in range(1, 16)]:
        assert original in INDUSTRIES


def test_dataset_records_complete_and_in_range():
    for i in INDUSTRIES.values():
        assert i.id and i.name and i.industry_type and i.city
        assert -90 <= i.latitude <= 90
        assert -180 <= i.longitude <= 180
        assert "DEMO" in i.name and "DEMO" in i.data_note


def test_dataset_spread_across_maharashtra_and_beyond():
    cities = {i.city for i in INDUSTRIES.values()}
    expected = {"Pune", "Mumbai", "Nashik", "Nagpur", "Kolhapur", "Solapur", "Thane"}
    assert expected <= cities


def test_dataset_size_in_demo_range():
    assert 20 <= len(INDUSTRIES) <= 30


# --------------------------------------------------------------------------- #
# RADIUS demonstration (10 / 25 / 50 / 100 km)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("radius", [10, 25, 50, 100])
def test_radius_levels_work(radius):
    r = client.get("/gis/nearby/IND001", params={"radius_km": radius})
    assert r.status_code == 200
    body = r.json()
    assert body["radius_km"] == radius
    for item in body["results"]:
        assert item["distance_km"] <= radius
        assert item["within_radius"] is True
        assert 0 <= item["geographic_score"] <= 100
        assert item["feasibility"] in {"VERY_HIGH", "HIGH", "MODERATE", "LOW"}


def test_radius_growth_is_monotonic():
    counts = [
        client.get("/gis/nearby/IND001", params={"radius_km": r}).json()["count"]
        for r in (10, 25, 50, 100)
    ]
    assert counts == sorted(counts)


def test_nearby_response_fields_documented_contract():
    body = client.get("/gis/nearby/IND001", params={"radius_km": 50}).json()
    for item in body["results"]:
        assert {"distance_km", "within_radius", "geographic_score", "feasibility"} <= set(item)


# --------------------------------------------------------------------------- #
# REGRESSION: evaluate-matches contract intact
# --------------------------------------------------------------------------- #
PERSON1_PAYLOAD = {
    "source": {
        "id": "IND001",
        "name": "ABC Steel",
        "industry_type": "Steel",
        "location": "Pune",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "material": "Steel Slag",
        "quantity": 500,
        "unit": "tonnes/month",
    },
    "potential_uses": [
        "Cement production",
        "Road construction",
        "Aggregate manufacturing",
    ],
    "matches": [
        {
            "id": "IND005",
            "name": "XYZ Cement",
            "industry_type": "Cement",
            "location": "Pune",
            "latitude": 18.6000,
            "longitude": 73.8000,
        }
    ],
}


def test_evaluate_matches_contract_unchanged():
    r = client.post("/gis/evaluate-matches", json=PERSON1_PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    m = body["matches"][0]
    for key in (
        "distance_km",
        "within_radius",
        "geographic_score",
        "feasibility",
        "coordinate_source",
        "map_data",
    ):
        assert key in m, key
    assert m["coordinate_source"] == "payload"
    assert m["distance_km"] > 0


def test_evaluate_matches_still_rejects_precomputed_values():
    payload = {
        "source": {"id": "IND001"},
        "opportunities": [
            {
                "consumer_id": "IND005",
                "consumer_name": "XYZ Cement",
                "distance_km": 999.0,  # bogus - must be recomputed
                "geographic_score": 1,
                "feasibility": "LOW",
            }
        ],
    }
    m = client.post("/gis/evaluate-matches", json=payload).json()["matches"][0]
    assert m["distance_km"] == round(SVC.distance_km("IND001", "IND005"), 2)
    assert m["distance_km"] != 999.0


def test_person2_can_reach_distance_fields():
    """Person 2 consumes distance_km / method for transport calculations."""
    r = client.post(
        "/gis/evaluate",
        json={"source_id": "IND001", "consumer_id": "IND002", "max_radius_km": 50},
    )
    body = r.json()
    assert body["distance_km"] > 0
    assert body["method"] == "haversine"

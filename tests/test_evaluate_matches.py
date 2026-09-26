"""Tests: POST /gis/evaluate-matches (flexible batch evaluation)."""

from fastapi.testclient import TestClient

from backend.gis.service import get_default_service
from backend.main import app

client = TestClient(app)
SVC = get_default_service()


# --------------------------------------------------------------------------- #
# Shape B - rich payload: source with material/quantity + matches with coords
# --------------------------------------------------------------------------- #
RICH_PAYLOAD = {
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
        },
        {
            "id": "IND008",
            "name": "Road Materials Ltd",
            "industry_type": "Road Construction",
            "location": "Pune",
            "latitude": 18.7500,
            "longitude": 73.9500,
        },
    ],
}


def test_rich_payload_evaluates_every_match():
    r = client.post("/gis/evaluate-matches", json=RICH_PAYLOAD)
    assert r.status_code == 200
    body = r.json()

    assert body["count"] == 2
    assert body["evaluated"] == 2
    assert body["max_radius_km"] == 50.0
    assert body["potential_uses"] == RICH_PAYLOAD["potential_uses"]

    # Source echoes material context and RESOLVED coordinates.
    src = body["source"]
    assert src["material"] == "Steel Slag"
    assert src["quantity"] == 500 and src["unit"] == "tonnes/month"
    assert src["latitude"] == 18.5204 and src["longitude"] == 73.8567

    # Every match got a full geographic verdict, sorted nearest first.
    matches = body["matches"]
    assert [m["status"] for m in matches] == ["ok", "ok"]
    distances = [m["distance_km"] for m in matches]
    assert distances == sorted(distances)
    for m in matches:
        for key in (
            "consumer_id",
            "consumer_name",
            "distance_km",
            "within_radius",
            "geographic_score",
            "feasibility",
            "map_data",
        ):
            assert key in m, key
        assert 0 <= m["geographic_score"] <= 100
        assert m["feasibility"] in {"VERY_HIGH", "HIGH", "MODERATE", "LOW"}
        assert m["map_data"]["distance_km"] == m["distance_km"]
        assert m["map_data"]["method"] == "haversine"


def test_payload_coordinates_take_precedence_and_metadata_is_enriched():
    # The rich payload supplies explicit coordinates; they must be used for
    # distance while metadata (industry_type) is still enriched from the
    # dataset record with the same id.
    r = client.post("/gis/evaluate-matches", json=RICH_PAYLOAD)
    body = r.json()

    m5 = next(m for m in body["matches"] if m["consumer_id"] == "IND005")
    assert m5["latitude"] == 18.6000 and m5["longitude"] == 73.8000
    assert m5["coordinate_source"] == "payload"
    # Pune (18.5204, 73.8567) -> (18.6, 73.8) is ~10.7 km.
    assert 8 < m5["distance_km"] < 14
    assert m5["within_radius"] is True
    # Dataset enrichment still fills industry_type even though payload coords won.
    assert m5["industry_type"] == "Cement"

    m8 = next(m for m in body["matches"] if m["consumer_id"] == "IND008")
    assert m8["latitude"] == 18.7500 and m8["longitude"] == 73.9500
    assert m8["coordinate_source"] == "payload"


def test_id_only_resolution_uses_dataset_coordinates():
    payload = {
        "source": {"id": "IND001"},
        "opportunities": [{"consumer_id": "IND005"}],
    }
    r = client.post("/gis/evaluate-matches", json=payload)
    m = r.json()["matches"][0]
    ind5 = SVC.get_industry("IND005")
    assert m["latitude"] == ind5.latitude
    assert m["coordinate_source"] == "dataset"
    assert m["distance_km"] == round(SVC.distance_km("IND001", "IND005"), 2)


def test_off_dataset_id_uses_payload_coordinates():
    payload = {
        "source": {"id": "IND001"},
        "matches": [
            {
                "id": "EXT-900",
                "name": "External Depot",
                "latitude": 19.0760,
                "longitude": 72.8777,
            }
        ],
    }
    r = client.post("/gis/evaluate-matches", json=payload)
    assert r.status_code == 200
    m = r.json()["matches"][0]
    assert m["status"] == "ok"
    assert m["coordinate_source"] == "payload"
    # Pune -> Mumbai straight-line is ~120-150 km.
    assert 100 < m["distance_km"] < 160
    assert m["within_radius"] is False


# --------------------------------------------------------------------------- #
# Shape A - compact payload: opportunities with pre-computed numbers
# --------------------------------------------------------------------------- #
def test_compact_payload_numbers_are_recomputed_not_trusted():
    payload = {
        "source": {"id": "IND001", "name": "ABC Steel"},
        "opportunities": [
            {
                "consumer_id": "IND005",
                "consumer_name": "XYZ Cement",
                "distance_km": 13.32,          # bogus on purpose
                "within_radius": True,
                "geographic_score": 95,        # bogus on purpose
                "feasibility": "VERY_HIGH",
            },
            {
                "consumer_id": "IND008",
                "consumer_name": "Road Materials Ltd",
                "distance_km": 27.13,
                "within_radius": True,
                "geographic_score": 89,
                "feasibility": "VERY_HIGH",
            },
        ],
    }
    r = client.post("/gis/evaluate-matches", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["evaluated"] == 2

    by_id = {m["consumer_id"]: m for m in body["matches"]}
    # Recomputed from dataset coordinates, NOT the bogus payload numbers:
    assert by_id["IND005"]["distance_km"] != 13.32
    expected5 = round(SVC.distance_km("IND001", "IND005"), 2)
    assert by_id["IND005"]["distance_km"] == expected5
    assert by_id["IND005"]["within_radius"] == (expected5 <= 50)
    expected8 = round(SVC.distance_km("IND001", "IND008"), 2)
    assert by_id["IND008"]["distance_km"] == expected8


def test_compact_payload_matches_service_reference_implementation():
    payload = {
        "source": {"id": "IND001"},
        "opportunities": [{"consumer_id": c} for c in ("IND005", "IND008", "IND011")],
        "max_radius_km": 100,
    }
    r = client.post("/gis/evaluate-matches", json=payload)
    body = r.json()
    reference = {
        o.consumer_id: o.model_dump()
        for o in SVC.nearby_opportunities("IND001", ["IND005", "IND008", "IND011"], 100)
    }
    for m in body["matches"]:
        ref = reference[m["consumer_id"]]
        assert m["distance_km"] == ref["distance_km"]
        assert m["within_radius"] == ref["within_radius"]
        assert m["geographic_score"] == ref["geographic_score"]
        assert m["feasibility"] == ref["feasibility"]


# --------------------------------------------------------------------------- #
# Edge cases
# --------------------------------------------------------------------------- #
def test_mixed_resolvable_and_unresolvable_matches():
    payload = {
        "source": {"id": "IND001"},
        "matches": [
            {"id": "IND005", "name": "Known"},
            {"id": "EXT-777", "name": "No coords anywhere"},
        ],
    }
    r = client.post("/gis/evaluate-matches", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["evaluated"] == 1
    statuses = {m["consumer_id"]: m["status"] for m in body["matches"]}
    assert statuses["IND005"] == "ok"
    assert statuses["EXT-777"] == "unresolved"
    bad = next(m for m in body["matches"] if m["consumer_id"] == "EXT-777")
    assert bad["detail"]
    assert bad["distance_km"] is None
    # Unresolved entries sort to the end.
    assert body["matches"][-1]["consumer_id"] == "EXT-777"


def test_max_radius_km_override_applies():
    payload = {"source": {"id": "IND001"}, "opportunities": [{"consumer_id": "IND002"}]}
    inside = client.post("/gis/evaluate-matches", json={**payload, "max_radius_km": 50}).json()
    outside = client.post("/gis/evaluate-matches", json={**payload, "max_radius_km": 1}).json()
    assert inside["matches"][0]["within_radius"] is True
    assert inside["max_radius_km"] == 50.0
    assert outside["matches"][0]["within_radius"] is False
    assert outside["max_radius_km"] == 1.0
    # Distance is identical regardless of radius.
    assert inside["matches"][0]["distance_km"] == outside["matches"][0]["distance_km"]


def test_missing_source_rejected():
    r = client.post("/gis/evaluate-matches", json={"opportunities": []})
    assert r.status_code == 422


def test_empty_matches_returns_empty_evaluations():
    r = client.post(
        "/gis/evaluate-matches", json={"source": {"id": "IND001"}, "matches": []}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 0 and body["evaluated"] == 0 and body["matches"] == []


def test_city_fallback_without_coordinates():
    payload = {
        "source": {"id": "IND001"},
        "matches": [{"name": "Somewhere in Thane", "location": "Thane"}],
    }
    r = client.post("/gis/evaluate-matches", json=payload)
    assert r.status_code == 200
    m = r.json()["matches"][0]
    assert m["status"] == "ok"
    assert m["coordinate_source"].startswith("city:")


def test_unknown_source_id_with_payload_coordinates_still_works():
    payload = {
        "source": {"id": "NEW-1", "name": "New Plant", "latitude": 18.6, "longitude": 73.9},
        "opportunities": [{"consumer_id": "IND002"}],
    }
    r = client.post("/gis/evaluate-matches", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["source"]["coordinate_source"] == "payload"
    assert body["evaluated"] == 1

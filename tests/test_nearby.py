"""Tests: FEATURE 3 / 4 (radius filtering + nearby discovery) and the dataset."""

import pytest

from backend.gis.config import ScoringConfig
from backend.gis.service import GISService, IndustryNotFoundError, load_industries

INDUSTRIES = load_industries()


@pytest.fixture()
def service():
    return GISService(INDUSTRIES)


def test_dataset_loads_and_has_expected_shape():
    assert len(INDUSTRIES) >= 10
    sample = INDUSTRIES["IND001"]
    assert sample.name
    assert -90 <= sample.latitude <= 90
    assert -180 <= sample.longitude <= 180
    assert "DEMO" in sample.data_note


def test_get_industry_missing_id_raises():
    with pytest.raises(IndustryNotFoundError):
        GISService(INDUSTRIES).get_industry("IND999")


def test_nearby_results_are_sorted_and_within_radius(service):
    results = service.nearby("IND001", radius_km=50)
    assert results, "expected at least one neighbour within 50 km of IND001"
    distances = [r.distance_km for r in results]
    assert distances == sorted(distances)
    assert all(r.distance_km <= 50 for r in results)
    assert all(r.within_radius for r in results)
    assert all(r.industry_id != "IND001" for r in results)


def test_tiny_radius_returns_empty(service):
    assert service.nearby("IND001", radius_km=0.001) == []


def test_include_outside_radius_flags_items(service):
    results = service.nearby(
        "IND001", radius_km=50, include_outside_radius=True
    )
    assert any(not r.within_radius for r in results)
    assert any(r.within_radius for r in results)


def test_industry_type_filter(service):
    results = service.nearby("IND001", radius_km=5000, industry_type="Cement")
    assert results
    assert all(r.industry_type == "Cement" for r in results)


def test_candidate_whitelist_is_respected(service):
    results = service.nearby("IND001", radius_km=5000, candidates=["IND002", "IND003"])
    assert {r.industry_id for r in results} == {"IND002", "IND003"}


def test_invalid_radius_rejected(service):
    with pytest.raises(ValueError):
        service.nearby("IND001", radius_km=0)


def test_opportunities_contract_shape(service):
    opps = service.nearby_opportunities(
        "IND001", ["IND002", "IND004", "IND014"], max_radius_km=50
    )
    assert len(opps) == 3
    assert [o.distance_km for o in opps] == sorted(o.distance_km for o in opps)
    keys = set(opps[0].model_dump())
    assert keys == {
        "consumer_id",
        "consumer_name",
        "distance_km",
        "within_radius",
        "geographic_score",
        "feasibility",
    }


def test_evaluate_and_map_data(service):
    result = service.evaluate("IND001", "IND002", max_radius_km=50)
    assert "map_data" in result
    assert result["map_data"]["source"]["name"] == service.get_industry("IND001").name
    assert result["map_data"]["distance_km"] == result["distance_km"]


def test_config_is_injectable():
    strict = GISService(INDUSTRIES, config=ScoringConfig(max_radius_km=1))
    assert strict.nearby("IND001", radius_km=1) == []


def test_route_defaults_to_straight_line(service):
    info = service.route("IND001", "IND002")
    assert info["provider"] == "haversine"
    assert info["distance_km"] > 0
    assert info["duration_minutes"] is None

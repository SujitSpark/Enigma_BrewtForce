"""Tests: FEATURE 1 (coordinates) + FEATURE 2 (Haversine distance)."""

import math

import pytest

from backend.gis.coordinates import resolve_coordinate, validate_coordinates
from backend.gis.distance import distance_between, haversine_distance_km
from backend.gis.schemas import Coordinate


def test_same_coordinates_is_zero():
    assert haversine_distance_km(18.5204, 73.8567, 18.5204, 73.8567) == pytest.approx(0.0)


def test_one_degree_latitude_is_about_111_km():
    # 1 degree of latitude is ~111.19 km on a sphere.
    assert haversine_distance_km(0.0, 0.0, 1.0, 0.0) == pytest.approx(111.19, abs=0.5)


def test_one_degree_longitude_at_equator_matches_latitude():
    assert haversine_distance_km(0.0, 0.0, 0.0, 1.0) == pytest.approx(111.19, abs=0.5)


def test_distance_is_symmetric():
    a = haversine_distance_km(18.5204, 73.8567, 19.0760, 72.8777)
    b = haversine_distance_km(19.0760, 72.8777, 18.5204, 73.8567)
    assert a == pytest.approx(b, rel=1e-9)


def test_distance_between_accepts_coordinates_and_tuples():
    p1 = Coordinate(latitude=18.5204, longitude=73.8567)
    p2 = (19.0760, 72.8777)
    assert distance_between(p1, p2) == pytest.approx(
        distance_between(p1, Coordinate(latitude=19.0760, longitude=72.8777))
    )


def test_pune_to_mumbai_is_ballpark():
    # Straight-line Pune -> Mumbai is roughly 120-150 km.
    km = haversine_distance_km(18.5204, 73.8567, 19.0760, 72.8777)
    assert 100 < km < 160


def test_validate_coordinates_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_coordinates(91.0, 0.0)
    with pytest.raises(ValueError):
        validate_coordinates(0.0, 181.0)


def test_resolve_coordinate_prefers_explicit_coordinates():
    c = resolve_coordinate(latitude=18.5, longitude=73.8, city="Pune")
    assert c.latitude == 18.5 and c.longitude == 73.8


def test_resolve_coordinate_without_data_raises():
    with pytest.raises(ValueError):
        resolve_coordinate()

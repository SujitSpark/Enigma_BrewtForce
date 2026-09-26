"""Tests: FEATURE 5 (geographic feasibility score + radius boundary)."""

import pytest

from backend.gis.config import ScoringConfig
from backend.gis.feasibility import (
    evaluate_distance,
    feasibility_band,
    geographic_score,
    is_within_radius,
)


def test_zero_distance_scores_100():
    assert geographic_score(0.0) == 100


def test_score_is_monotonically_non_increasing():
    scores = [geographic_score(d) for d in range(0, 400, 5)]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


def test_score_is_anchored_at_25_km():
    # Anchor (25, 90) -> exactly 90 at the node.
    assert geographic_score(25.0) == 90


def test_score_clamped_at_500_km():
    assert geographic_score(5000.0) == 0


def test_feasibility_bands_match_documented_thresholds():
    assert feasibility_band(10) == "VERY_HIGH"
    assert feasibility_band(25) == "VERY_HIGH"  # inclusive upper edge
    assert feasibility_band(40) == "HIGH"
    assert feasibility_band(80) == "MODERATE"
    assert feasibility_band(400) == "LOW"


def test_negative_distance_rejected():
    with pytest.raises(ValueError):
        geographic_score(-1)
    with pytest.raises(ValueError):
        feasibility_band(-1)


def test_radius_boundary_is_inclusive():
    assert is_within_radius(50.0, 50.0) is True
    assert is_within_radius(50.01, 50.0) is False


def test_evaluate_distance_shape_and_flags():
    result = evaluate_distance(22.4, 50)
    assert set(result) == {
        "distance_km",
        "max_radius_km",
        "within_radius",
        "geographic_score",
        "feasibility",
        "method",
    }
    assert result["within_radius"] is True
    assert result["method"] == "haversine"
    assert 0 <= result["geographic_score"] <= 100


def test_evaluate_distance_outside_radius():
    result = evaluate_distance(67.2, 50)
    assert result["within_radius"] is False


def test_thresholds_are_configurable():
    custom = ScoringConfig(
        max_radius_km=10,
        bands=[(5.0, "NEAR"), (float("inf"), "FAR")],
        score_anchors=[(0.0, 100), (10.0, 0)],
    )
    assert feasibility_band(3, custom) == "NEAR"
    assert feasibility_band(6, custom) == "FAR"
    assert geographic_score(5, custom) == 50

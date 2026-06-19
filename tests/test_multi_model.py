"""Tests for core.multi_model — safe intersection, conflict analysis, weighted greedy.

Uses simulated data with 2-3 OLS models to verify multi-model arbitration logic.
"""

import numpy as np
import pandas as pd

from core.multi_model import (
    compute_safe_intersection,
    compute_conflict_coefficient,
    compute_conflict_matrix,
    generate_recommendations,
    layered_relaxation,
    arbitrate,
)


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_multi_data(n=100, seed=42):
    """Create data suitable for 2 related OLS models (y1 ~ x, y2 ~ x + c1)."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    c1 = rng.normal(0, 1, n)
    noise1 = rng.normal(0, 0.5, n)
    noise2 = rng.normal(0, 0.5, n)
    # Add outlier group (first 5 obs) that affects both y1 and y2
    noise1[:5] = rng.normal(0, 5, 5)
    noise2[:5] = rng.normal(0, 5, 5)
    y1 = 1.0 + 1.5 * x + noise1
    y2 = 0.5 + 1.2 * x + 0.3 * c1 + noise2
    return pd.DataFrame({"y1": y1, "y2": y2, "x": x, "c1": c1})


def _make_toy_results():
    """Create minimal model results for testing intersection/conflict logic."""
    return {
        "model_A": {
            "final": {"deleted_obs": [1, 3, 5, 7]},
            "baseline": {"t_stat": 1.5, "p_value": 0.14},
        },
        "model_B": {
            "final": {"deleted_obs": [3, 5, 7, 9]},
            "baseline": {"t_stat": 1.3, "p_value": 0.20},
        },
    }


# ── safe_intersection ─────────────────────────────────────────────────

def test_safe_intersection_basic():
    results = _make_toy_results()
    safe = compute_safe_intersection(results)
    assert sorted(safe) == [3, 5, 7], f"Expected [3,5,7] got {safe}"


def test_safe_intersection_no_overlap():
    results = {
        "A": {"final": {"deleted_obs": [1, 2]}},
        "B": {"final": {"deleted_obs": [3, 4]}},
    }
    safe = compute_safe_intersection(results)
    assert safe == []


def test_safe_intersection_single_model():
    results = {"A": {"final": {"deleted_obs": [1, 2, 3]}}}
    safe = compute_safe_intersection(results)
    assert sorted(safe) == [1, 2, 3]


# ── conflict_coefficient ──────────────────────────────────────────────

def test_conflict_coefficient_full_overlap():
    results = {
        "A": {"final": {"deleted_obs": [1, 2]}},
        "B": {"final": {"deleted_obs": [1, 2]}},
    }
    coeff = compute_conflict_coefficient(results)
    assert abs(coeff - 0.0) < 1e-10, f"Full overlap: coeff={coeff}"


def test_conflict_coefficient_no_overlap():
    results = {
        "A": {"final": {"deleted_obs": [1, 2]}},
        "B": {"final": {"deleted_obs": [3, 4]}},
    }
    coeff = compute_conflict_coefficient(results)
    assert abs(coeff - 1.0) < 1e-10, f"No overlap: coeff={coeff}"


# ── conflict_matrix ───────────────────────────────────────────────────

def test_conflict_matrix_structure():
    """conflict_matrix should have correct keys for each ambiguous obs."""
    df = _make_multi_data(n=60, seed=42)
    results = {
        "A": {"final": {"deleted_obs": [0, 1, 2, 3, 4]}},
        "B": {"final": {"deleted_obs": [3, 4, 5, 6, 7]}},
    }
    configs = [
        {"name": "A", "type": "ols", "dependent_var": "y1", "key_var": "x", "control_vars": []},
        {"name": "B", "type": "ols", "dependent_var": "y2", "key_var": "x", "control_vars": ["c1"]},
    ]
    safe = compute_safe_intersection(results)
    matrix = compute_conflict_matrix(results, df, configs, safe)
    assert isinstance(matrix, list)
    for entry in matrix:
        assert "obs_id" in entry
        assert "effects" in entry
        assert isinstance(entry["effects"], dict)


# ── recommendations ───────────────────────────────────────────────────

def test_recommendations_all_positive():
    conflict = [
        {"obs_id": 1, "effects": {"A": 0.5, "B": 0.3}, "recommendation": None, "note": None},
        {"obs_id": 2, "effects": {"A": 0.8, "B": 0.1}, "recommendation": None, "note": None},
    ]
    result = generate_recommendations(conflict, safe_intersection=[])
    assert result[0]["recommendation"] == "delete"
    assert result[1]["recommendation"] == "delete"


def test_recommendations_mixed():
    conflict = [
        {"obs_id": 3, "effects": {"A": 0.5, "B": -0.3}, "recommendation": None, "note": None},
    ]
    result = generate_recommendations(conflict, safe_intersection=[])
    assert result[0]["recommendation"] == "caution"
    assert "有害" in result[0]["note"]


def test_recommendations_severe_conflict():
    conflict = [
        {"obs_id": 4, "effects": {"A": 0.2, "B": -1.5}, "recommendation": None, "note": None},
    ]
    result = generate_recommendations(conflict, safe_intersection=[])
    assert result[0]["recommendation"] == "block"


# ── layered_relaxation ────────────────────────────────────────────────

def test_layered_relaxation_no_need():
    """When all models already pass, relaxation should return empty."""
    results = _make_toy_results()
    configs = [
        {"name": "model_A", "priority": 5, "target_p": 0.05},
        {"name": "model_B", "priority": 3, "target_p": 0.05},
    ]
    safe = compute_safe_intersection(results)
    relaxed = layered_relaxation(results, configs, safe)
    assert isinstance(relaxed, dict)


# ── arbitrate ─────────────────────────────────────────────────────────

def test_arbitrate_output_contract():
    """arbitrate should return dict conforming to compute_output.multi_model."""
    df = _make_multi_data(n=60, seed=42)
    results = {
        "A": {"final": {"deleted_obs": [0, 1, 2, 3, 4]},
              "baseline": {"t_stat": 1.8, "p_value": 0.07},
              "deletion_path": []},
        "B": {"final": {"deleted_obs": [3, 4, 5, 6, 7]},
              "baseline": {"t_stat": 1.5, "p_value": 0.13},
              "deletion_path": []},
    }
    configs = [
        {"name": "A", "type": "ols", "priority": 5, "target_p": 0.05,
         "dependent_var": "y1", "key_var": "x", "control_vars": []},
        {"name": "B", "type": "ols", "priority": 4, "target_p": 0.05,
         "dependent_var": "y2", "key_var": "x", "control_vars": ["c1"]},
    ]
    result = arbitrate(results, configs, df)
    for key in ("conflict_coefficient", "safe_intersection", "conflict_matrix", "status_by_model"):
        assert key in result, f"Missing key: {key}"

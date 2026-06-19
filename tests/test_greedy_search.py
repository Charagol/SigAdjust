"""Tests for core.greedy_search — greedy iterative deletion algorithm."""

import numpy as np
import pandas as pd
from core.greedy_search import greedy_deletion


def _make_data_with_outliers(n=100, seed=42):
    """Create data where a few observations drag down the key variable''s t-value."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    c1 = rng.normal(0, 1, n)
    noise = rng.normal(0, 1, n)

    # Make first 5 obs "outliers": large noise → lower t for x
    noise[:5] = rng.normal(0, 8, 5)

    y = 2.0 * x + 0.5 * c1 + noise
    return pd.DataFrame({"y": y, "x": x, "c1": c1})


def test_greedy_deletion_returns_contract():
    df = _make_data_with_outliers()
    result = greedy_deletion(df, "y", "x", ["c1"], 0.05, 10.0)

    assert "baseline" in result
    assert "deletion_path" in result
    assert "final" in result
    assert "spec_curves" in result

    baseline = result["baseline"]
    assert isinstance(baseline["p_value"], float)
    assert baseline["n_obs"] == 100


def test_greedy_deletion_stops_within_budget():
    df = _make_data_with_outliers()
    max_pct = 5.0  # max 5 obs
    result = greedy_deletion(df, "y", "x", ["c1"], 0.05, max_pct)

    n_deleted = result["final"]["n_deleted"]
    assert n_deleted <= 5


def test_greedy_deletion_t_monotonic_or_stop():
    """Verify t-value doesn''t decrease across deletion steps (greedy should improve or stop)."""
    df = _make_data_with_outliers()
    result = greedy_deletion(df, "y", "x", ["c1"], 0.01, 10.0)

    path = result["spec_curves"][0]["path"]
    for i in range(1, len(path)):
        assert abs(path[i]["t"]) >= abs(path[i-1]["t"]) - 0.01, (
            f"t dropped from {path[i-1]['t']} to {path[i]['t']} at step {i}"
        )


def test_greedy_deletion_no_control_vars():
    """Works with no control variables."""
    df = _make_data_with_outliers()
    result = greedy_deletion(df, "y", "x", [], 0.05, 10.0)
    assert result["baseline"]["n_obs"] == 100


def test_greedy_deletion_obs_ids_are_unique():
    df = _make_data_with_outliers()
    result = greedy_deletion(df, "y", "x", ["c1"], 0.05, 10.0)

    deleted = result["final"]["deleted_obs"]
    assert len(deleted) == len(set(deleted)), "Duplicate obs in deleted set"

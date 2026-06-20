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

def test_direction_both_equals_original():
    u"direction=both should produce identical results to not passing direction."
    rng = np.random.default_rng(42)
    n = 50
    x = rng.normal(0, 1, n)
    y = 2.0 * x + rng.normal(0, 0.5, n)
    y[:3] = y[:3] + rng.normal(0, 5, 3)
    df = pd.DataFrame({"y": y, "x": x})

    result_default = greedy_deletion(df, "y", "x", [], 0.05, 10.0)
    result_both = greedy_deletion(df, "y", "x", [], 0.05, 10.0, direction="both")

    assert result_both["final"]["n_deleted"] == result_default["final"]["n_deleted"]
    assert result_both["final"]["t_stat"] == result_default["final"]["t_stat"]
    assert result_both["final"]["beta"] == result_default["final"]["beta"]
    assert result_both["deletion_path"] == result_default["deletion_path"]
    assert result_both["spec_curves"] == result_default["spec_curves"]




def test_direction_positive_flip():
    u"_apply_direction_filter sign_flip phase for positive direction."
    from core.greedy_search import _apply_direction_filter as adf
    t_del = np.array([1.5, 2.0, -1.0, 0.5, 3.0])
    current_t = -0.5
    current_beta = -0.8
    beta_del = np.array([-0.3, 0.1, -0.9, -0.5, 0.3])
    # direction=positive: delta = beta_del - current_beta
    # = [0.5, 0.9, -0.1, 0.3, 1.1]
    # Qualifying: 0,1,3,4. Best: 4 (delta=1.1)
    scores, phase = adf(t_del, current_t, current_beta, beta_del, "positive")
    assert phase == "sign_flip"
    assert int(np.argmax(scores)) == 4
    # Non-qualifying candidate gets score 0
    assert scores[2] == 0.0
    assert scores[4] > scores[1]  # best beats second-best


def test_direction_negative_flip():
    u"_apply_direction_filter sign_flip phase for negative direction."
    from core.greedy_search import _apply_direction_filter as adf
    t_del = np.array([1.5, -1.0, 0.5])
    current_t = 0.5
    current_beta = 0.8
    beta_del = np.array([0.3, -0.2, 0.7])
    # direction=negative: delta = current_beta - beta_del
    # = [0.5, 1.0, 0.1]
    # All qualify. Best: idx 1 (delta=1.0)
    scores, phase = adf(t_del, current_t, current_beta, beta_del, "negative")
    assert phase == "sign_flip"
    assert int(np.argmax(scores)) == 1
    assert np.all(scores >= 0)

def test_direction_stops_when_no_candidates():
    u"Direction filter eliminates all candidates; should not crash."
    rng = np.random.default_rng(42)
    n = 10
    x = np.concatenate([rng.normal(-2.0, 0.3, 8), rng.normal(5.0, 0.3, 2)])
    y = 5.0 + (-1.0) * x + rng.normal(0, 0.3, 10)
    df = pd.DataFrame({"y": y, "x": x})

    result = greedy_deletion(df, "y", "x", [], 0.05, 30.0, direction="positive")

    assert "baseline" in result
    assert "final" in result
    assert isinstance(result["final"]["n_deleted"], int)
    assert "direction_achieved" in result["final"]

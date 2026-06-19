"""Tests for core.models.logit_model -- Logit / Probit fitting and greedy deletion.

Key verification: statsmodels Logit get_influence().dfbetas returns standardized
dfbetas (units = standard error). Formula: t_approx = beta/bse - dfbetas.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import pytest
import warnings

from core.models.logit_model import fit_logit, run_logit_greedy, _compute_logit_deletion_t


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_binary_data(n=50, seed=42):
    """Small binary classification dataset with one outlier group."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    c1 = rng.normal(0, 1, n)
    noise = rng.normal(0, 0.5, n)
    z = 0.5 + 1.5 * x + 0.3 * c1 + noise
    # Make first few obs harder to predict (add outlier noise)
    n_out = min(5, n)
    if n_out > 0:
        noise[:n_out] = rng.normal(0, 3, n_out)
        z[:n_out] = 0.5 + 1.5 * x[:n_out] + 0.3 * c1[:n_out] + noise[:n_out]
    p = 1 / (1 + np.exp(-z))
    y = (rng.random(n) < p).astype(int)
    return pd.DataFrame({"y": y, "x": x, "c1": c1})


# ── fit_logit ─────────────────────────────────────────────────────────

def test_fit_logit_returns_contract():
    """fit_logit should return baseline + diagnostics matching OLS format."""
    df = _make_binary_data()
    result = fit_logit(df, "y", "x", ["c1"], model_type="logit")
    assert "baseline" in result
    assert "diagnostics" in result
    b = result["baseline"]
    for key in ("beta", "se", "t_stat", "p_value", "r_squared", "n_obs", "df"):
        assert key in b, f"Missing key: {key}"
    assert isinstance(b["beta"], float)
    assert b["n_obs"] == 50
    assert 0 <= b["r_squared"] <= 1


def test_fit_probit_returns_contract():
    """fit_logit with model_type='probit' should also work."""
    df = _make_binary_data()
    result = fit_logit(df, "y", "x", ["c1"], model_type="probit")
    b = result["baseline"]
    assert b["n_obs"] == 50
    assert "beta" in b


# ── dfbetas interpretation ────────────────────────────────────────────

def test_dfbetas_interpretation():
    """Verify statsmodels Logit dfbetas are standardized (units=SE).

    At n=200 the one-step Newton approximation is reliable enough to
    distinguish which interpretation is correct.
    """
    df = _make_binary_data(n=200, seed=99)
    X = sm.add_constant(df[["x", "c1"]])
    model = sm.Logit(df["y"], X).fit(disp=0)
    infl = model.get_influence()

    beta = model.params["x"]
    bse = model.bse["x"]

    # A) Standardized: t = beta/bse - dfbetas
    t_std = beta / bse - infl.dfbetas[:, 1]
    # B) Raw: t = (beta - dfbetas) / bse
    t_raw = (beta - infl.dfbetas[:, 1]) / bse

    # Ground truth: LOO refit for first 3 observations
    n = len(df)
    t_loo = np.zeros(3)
    for i in range(3):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m_loo = sm.Logit(df["y"].values[mask], X.values[mask]).fit(disp=0)
        t_loo[i] = m_loo.tvalues[1]

    err_std = np.abs(t_std[:3] - t_loo).mean()
    err_raw = np.abs(t_raw[:3] - t_loo).mean()
    assert err_std < err_raw, (
        f"Standardized dfbetas wins: std_err={err_std:.4f} < raw_err={err_raw:.4f}"
    )


# ── _compute_logit_deletion_t ─────────────────────────────────────────

def test_compute_logit_deletion_t():
    """_compute_logit_deletion_t should return (N,) array of t-values."""
    df = _make_binary_data(n=30, seed=42)
    X = sm.add_constant(df[["x", "c1"]])
    model = sm.Logit(df["y"], X).fit(disp=0)
    infl = model.get_influence()

    t_del = _compute_logit_deletion_t(
        infl.dfbetas,
        model.params.values,
        model.bse.values,
        key_var_index=1,
    )
    assert t_del.shape == (30,)
    assert np.all(np.isfinite(t_del))


# ── run_logit_greedy ──────────────────────────────────────────────────

def test_run_logit_greedy_returns_contract():
    """run_logit_greedy should return the same dict structure as greedy_deletion."""
    df = _make_binary_data(n=50, seed=42)
    result = run_logit_greedy(
        df, "y", "x", ["c1"],
        significance_threshold=0.05,
        max_deletions_pct=5.0,
        model_type="logit",
        exact=True,
    )
    for key in ("baseline", "deletion_path", "final", "spec_curves"):
        assert key in result, f"Missing key: {key}"
    assert result["baseline"]["n_obs"] == 50


def test_run_logit_greedy_exact_approximate_ranking_consistent():
    """Exact and approximate modes should produce same first deletion."""
    df = _make_binary_data(n=50, seed=42)

    r_exact = run_logit_greedy(
        df, "y", "x", ["c1"],
        significance_threshold=0.01,
        max_deletions_pct=10.0,
        model_type="logit",
        exact=True,
    )
    r_approx = run_logit_greedy(
        df, "y", "x", ["c1"],
        significance_threshold=0.01,
        max_deletions_pct=10.0,
        model_type="logit",
        exact=False,
    )

    exact_first = r_exact["deletion_path"][0]["obs_id"] if r_exact["deletion_path"] else None
    approx_first = r_approx["deletion_path"][0]["obs_id"] if r_approx["deletion_path"] else None

    if exact_first is not None and approx_first is not None:
        assert exact_first == approx_first, (
            f"First deletion differs: exact={exact_first}, approx={approx_first}"
        )

"""Tests for core.models.iv_model -- CFA-based 2SLS with dual-stage diagnostics.

CFA (Control Function Approach): 2SLS decomposed into two OLS regressions.
CFA beta on endogenous var = IV2SLS beta (numerically exact).
Deletion priority based on stage-2 t-value (significance target).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.sandbox.regression.gmm import IV2SLS
from core.models.iv_model import fit_iv, run_iv_greedy


def _make_iv_data(n=80, seed=42):
    """Create data with endogenous x and valid instrument z."""
    rng = np.random.default_rng(seed)
    z = rng.normal(0, 1, n)
    v = rng.normal(0, 0.5, n)
    x = 0.7 * z + v  # endogenous (correlated with error via v)
    c1 = rng.normal(0, 1, n)
    noise = 0.5 * v + rng.normal(0, 0.3, n)  # error correlated with v
    noise[:5] = rng.normal(0, 5, 5)  # outliers
    y = 1.0 + 2.0 * x + 0.3 * c1 + noise
    return pd.DataFrame({"y": y, "x": x, "z": z, "c1": c1})


def test_cfa_beta_equals_2sls():
    """CFA stage-2 beta on endogenous var must equal statsmodels IV2SLS beta."""
    df = _make_iv_data(n=80, seed=42)

    # --- CFA: fit_iv ---
    result = fit_iv(df, "y", "x", ["c1"], endogenous_var="x", instruments=["z"])
    beta_cfa = result["baseline"]["beta"]

    # --- IV2SLS: identical X construction ---
    exog = sm.add_constant(df[["x", "c1"]])
    endog = df["y"]
    instr = sm.add_constant(df[["z", "c1"]])
    iv_model = IV2SLS(endog, exog, instr).fit()
    beta_2sls = iv_model.params["x"]

    assert abs(beta_cfa - beta_2sls) < 1e-10, (
        f"CFA beta={beta_cfa:.8f}, IV2SLS beta={beta_2sls:.8f}"
    )


def test_fit_iv_returns_contract():
    """fit_iv should return baseline with stage2 t/p, stage1 F, and diagnostics."""
    df = _make_iv_data()
    result = fit_iv(df, "y", "x", ["c1"], endogenous_var="x", instruments=["z"])

    assert "baseline" in result
    assert "diagnostics" in result
    b = result["baseline"]
    for key in ("beta", "se", "t_stat", "p_value", "r_squared", "n_obs", "df", "stage1_f"):
        assert key in b, f"Missing key: {key}"
    assert b["n_obs"] == 80
    assert b["stage1_f"] > 0  # Should have some explanatory power


def test_run_iv_greedy_returns_contract():
    """run_iv_greedy should return standard dict with deletion_path and spec_curves."""
    df = _make_iv_data(n=60, seed=42)
    result = run_iv_greedy(
        df, "y", "x", ["c1"],
        endogenous_var="x", instruments=["z"],
        significance_threshold=0.05, max_deletions_pct=10.0,
    )
    for key in ("baseline", "deletion_path", "final", "spec_curves"):
        assert key in result
    assert result["baseline"]["n_obs"] == 60


def test_stage1_f_tracked():
    """Stage-1 F-statistic should appear in baseline and remain finite."""
    df = _make_iv_data(n=80, seed=42)
    result = fit_iv(df, "y", "x", ["c1"], endogenous_var="x", instruments=["z"])
    f_val = result["baseline"]["stage1_f"]
    assert 0 < f_val < 1e6, f"Stage-1 F out of range: {f_val}"

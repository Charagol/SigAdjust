"""Tests for core.models.fe_model — Fixed Effects FWL strategy.

FWL theorem: demeaning by groups produces identical beta point estimates
as full fixed effects regression. Standard errors differ slightly because
the demeaned OLS does not account for df used by FE absorption.
"""

import numpy as np
import pandas as pd
from core.models.fe_model import fit_fe, run_fe_greedy


def _make_panel_data(n_firms=10, n_years=5, seed=42):
    """Balanced panel with firm-level FE and one outlier group."""
    rng = np.random.default_rng(seed)
    total = n_firms * n_years
    firm = np.repeat(np.arange(n_firms), n_years)
    year = np.tile(np.arange(n_years), n_firms)

    # Firm-level FE
    firm_effect = rng.normal(0, 2, n_firms)
    firm_fe = firm_effect[firm]

    x = 0.5 * firm_fe + rng.normal(0, 1, total)
    c1 = rng.normal(0, 1, total)
    noise = rng.normal(0, 0.5, total)

    # Add outlier to first 3 firms (one obs each)
    noise[0] = rng.normal(0, 5)
    noise[n_years] = rng.normal(0, 5)
    noise[2 * n_years] = rng.normal(0, 5)

    y = 1.0 + 1.5 * x + 0.3 * c1 + firm_fe + noise
    return pd.DataFrame({"y": y, "x": x, "c1": c1, "firm": firm, "year": year})


def test_fit_fe_returns_contract():
    """fit_fe should return baseline + diagnostics matching OLS format."""
    df = _make_panel_data()
    result = fit_fe(df, "y", "x", ["c1"], fe_vars=["firm", "year"])

    assert "baseline" in result
    assert "diagnostics" in result
    b = result["baseline"]
    for key in ("beta", "se", "t_stat", "p_value", "r_squared", "n_obs", "df"):
        assert key in b, f"Missing key: {key}"
    assert isinstance(b["beta"], float)
    assert b["n_obs"] == 50

    # Diagnostics should include standard OLSInfluence fields
    diag = result["diagnostics"]
    assert "params_not_obsi" in diag
    assert "sigma2_not_obsi" in diag
    assert "XtX_inv_diag" in diag


def test_fit_fe_beta_matches_pyfixest():
    """FWL-demeaned OLS beta should match pyfixest feols beta exactly."""
    df = _make_panel_data()
    result = fit_fe(df, "y", "x", ["c1"], fe_vars=["firm"])

    # Compare with pyfixest directly
    import pyfixest as pf
    m_pf = pf.feols("y ~ x + c1 | firm", data=df)
    beta_pf = m_pf.coef()["x"]

    beta_fwl = result["baseline"]["beta"]
    assert abs(beta_fwl - beta_pf) < 1e-10, (
        f"FWL beta={beta_fwl:.6f} != pyfixest beta={beta_pf:.6f}"
    )


def test_run_fe_greedy_returns_contract():
    """run_fe_greedy should return standard greedy_deletion dict structure."""
    df = _make_panel_data()
    result = run_fe_greedy(
        df, "y", "x", ["c1"],
        fe_vars=["firm"],
        significance_threshold=0.05,
        max_deletions_pct=10.0,
    )
    for key in ("baseline", "deletion_path", "final", "spec_curves"):
        assert key in result, f"Missing key: {key}"
    assert result["baseline"]["n_obs"] == 50

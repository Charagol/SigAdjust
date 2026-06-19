"""Tests for core.models.ols_model — OLS fitting and diagnostics."""

import numpy as np
import pandas as pd
from core.models.ols_model import fit_ols


def make_sample_data(n=50, seed=42):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    c1 = rng.normal(2, 0.5, n)
    c2 = rng.normal(-1, 1, n)
    noise = rng.normal(0, 0.5, n)
    y = 1.0 + 1.5 * x + 0.3 * c1 - 0.2 * c2 + noise
    return pd.DataFrame({"y": y, "x": x, "c1": c1, "c2": c2})


def test_fit_ols_returns_baseline():
    df = make_sample_data()
    result = fit_ols(df, "y", "x", ["c1", "c2"])
    baseline = result["baseline"]

    assert "beta" in baseline
    assert "p_value" in baseline
    assert "r_squared" in baseline
    assert baseline["n_obs"] == 50
    assert isinstance(baseline["beta"], float)


def test_fit_ols_diagnostics_structure():
    df = make_sample_data()
    result = fit_ols(df, "y", "x", ["c1", "c2"])
    diag = result["diagnostics"]

    assert "params_not_obsi" in diag
    assert "sigma2_not_obsi" in diag
    assert "XtX_inv_diag" in diag
    assert "key_var_index" in diag
    assert diag["params_not_obsi"].shape == (50, 4)  # 50 obs, const + x + c1 + c2

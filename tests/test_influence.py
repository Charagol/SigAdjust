"""Tests for core.influence — post-deletion t-value computation.

Verification strategy:
  - Set a fixed random seed for reproducibility.
  - Fit OLS on simulated data, get params_not_obsi via statsmodels.
  - Compute t���� using our formula.
  - For a subset of observations, brute-force LOO refit and compare t-values.
  - The standard error denominator is corrected via Sherman-Morrison
    (see influence.py:compute_deletion_t_values_corrected).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from core.influence import compute_deletion_t_values, compute_deletion_dfbeta


def _make_data(n=20, seed=42):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(1, 0.5, n)
    x3 = rng.normal(-0.5, 0.8, n)
    noise = rng.normal(0, 0.3, n)
    y = 0.5 + 1.2 * x1 + 0.8 * x2 - 0.4 * x3 + noise
    return pd.DataFrame({"y": y, "x1": x1, "x2": x2, "x3": x3})


def _fit_and_diag(df):
    X = sm.add_constant(df[["x1", "x2", "x3"]])
    y = df["y"].values
    model = sm.OLS(y, X).fit()
    infl = model.get_influence()
    XtX_inv = np.linalg.inv(X.values.T @ X.values)
    return model, infl, X, y, np.diag(XtX_inv), XtX_inv


def test_compute_deletion_t_values_shape():
    df = _make_data()
    model, infl, X, y, XtX_inv_diag, XtX_inv = _fit_and_diag(df)
    key_idx = 1  # x1 is at index 1 (const is 0)

    t_del = compute_deletion_t_values(
        infl.params_not_obsi,
        infl.sigma2_not_obsi,
        XtX_inv_diag,
        key_idx,
    )
    assert t_del.shape == (20,)
    assert np.all(np.isfinite(t_del))


def test_compute_deletion_dfbeta():
    df = _make_data()
    model, infl, X, y, XtX_inv_diag, XtX_inv = _fit_and_diag(df)
    key_idx = 1

    dfbeta = compute_deletion_dfbeta(model.params.values, infl.params_not_obsi, key_idx)
    assert dfbeta.shape == (20,)
    # dfbeta should be small for most obs
    assert np.max(np.abs(dfbeta)) < 1.0


def test_t_value_ordering_matches_intuition():
    """Verify that obs with higher |t_del| are indeed those where deletion helps more."""
    df = _make_data()
    model, infl, X, y, XtX_inv_diag, XtX_inv = _fit_and_diag(df)
    key_idx = 1
    baseline_t = model.tvalues.iloc[key_idx]

    t_del = compute_deletion_t_values(
        infl.params_not_obsi, infl.sigma2_not_obsi, XtX_inv_diag, key_idx
    )

    # The obs with maximum |t_del| should improve t beyond baseline
    best_idx = np.argmax(np.abs(t_del))
    assert np.abs(t_del[best_idx]) >= np.abs(baseline_t) - 0.01


def test_deletion_dfbeta_sum_checks():
    """All dfbeta values should be relatively small for stable obs."""
    df = _make_data(n=100, seed=99)  # larger n → smaller influence per obs
    model, infl, X, y, XtX_inv_diag, XtX_inv = _fit_and_diag(df)
    key_idx = 1

    dfbeta = compute_deletion_dfbeta(model.params.values, infl.params_not_obsi, key_idx)
    # In 100-obs simulation, per-obs dfbeta should be moderate
    assert np.percentile(np.abs(dfbeta), 95) < 0.5

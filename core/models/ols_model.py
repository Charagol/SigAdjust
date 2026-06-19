"""OLS model fitting and diagnostics via statsmodels.

Encapsulates sm.OLS fitting and OLSInfluence diagnostic extraction.
Returns standard dict format — no Streamlit dependency.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def fit_ols(
    df: pd.DataFrame,
    dependent_var: str,
    key_var: str,
    control_vars: list[str],
) -> dict:
    """Fit OLS model and extract baseline estimates + diagnostics.

    Args:
        df: Input DataFrame.
        dependent_var: Name of the dependent variable column.
        key_var: Name of the key explanatory variable (tracked through deletion).
        control_vars: List of control variable column names.

    Returns:
        Dict with keys "baseline" and "diagnostics" (see below).
    """
    # ── Build design matrix
    all_vars = [key_var] + [v for v in control_vars if v != key_var]
    X = df[all_vars].copy()
    X = sm.add_constant(X)
    y = df[dependent_var].values

    model = sm.OLS(y, X).fit()
    infl = model.get_influence()

    # ── Locate key_var index in X (after add_constant)
    key_idx = list(X.columns).index(key_var)

    # ── Compute (X'X)⁻¹ diagonal for SE calculations
    XtX_inv = np.linalg.inv(X.values.T @ X.values)
    XtX_inv_diag = np.diag(XtX_inv)

    baseline = {
        "beta": float(model.params[key_var]),
        "se": float(model.bse[key_var]),
        "t_stat": float(model.tvalues[key_var]),
        "p_value": float(model.pvalues[key_var]),
        "r_squared": float(model.rsquared),
        "n_obs": int(model.nobs),
        "df": int(model.df_resid),
    }

    diagnostics = {
        "hat_matrix_diag": infl.hat_matrix_diag,
        "resid": model.resid.values,
        "dfbetas": infl.dfbetas,
        "sigma2_not_obsi": infl.sigma2_not_obsi,
        "params_not_obsi": infl.params_not_obsi,
        "X": X.values,
        "XtX_inv_diag": XtX_inv_diag,
        "key_var_index": key_idx,
        "beta_vector": model.params.values,
    }

    return {"baseline": baseline, "diagnostics": diagnostics}

"""2SLS / IV model via Control Function Approach (CFA).

CFA decomposes 2SLS into two OLS regressions:
  Stage 1: endogenous ~ instruments + controls + const  -> residuals v_hat
  Stage 2: dependent   ~ endogenous + v_hat + controls + const

Key properties:
  - CFA beta_hat on endogenous = 2SLS beta_hat (numerically exact).
  - Both stages are OLS -> standard OLSInfluence diagnostics apply.
  - Deletion priority based on stage-2 t-value (significance target).
  - Stage-1 F-statistic tracked to monitor instrument strength.

Limitation: CFA-OLS standard errors omit first-stage sampling error.
For ranking purposes (greedy deletion sort) the precision is sufficient.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from core.influence import compute_deletion_t_values
from core.greedy_search import _apply_direction_filter


def _run_stage1(df, endogenous_var, instruments, control_vars):
    """Run first-stage regression: endogenous ~ instruments + controls."""
    s1_vars = instruments + [v for v in control_vars if v not in instruments]
    X1 = sm.add_constant(df[s1_vars].copy())
    y1 = df[endogenous_var].values
    model1 = sm.OLS(y1, X1).fit()
    v_hat = model1.resid
    f_stat = model1.fvalue
    return model1, v_hat, f_stat


def _run_stage2(df, dependent_var, endogenous_var, v_hat, control_vars):
    """Run second-stage (CFA) regression including first-stage residuals."""
    s2_vars = [endogenous_var] + [v for v in control_vars if v != endogenous_var]
    X2_raw = df[s2_vars].copy()
    X2_raw["__v_hat__"] = v_hat
    X2 = sm.add_constant(X2_raw)
    y2 = df[dependent_var].values
    model2 = sm.OLS(y2, X2).fit()
    return model2, X2


def fit_iv(
    df: pd.DataFrame,
    dependent_var: str,
    key_var: str,
    control_vars: list[str],
    endogenous_var: str,
    instruments: list[str],
) -> dict:
    """Fit 2SLS via CFA and extract dual-stage diagnostics.

    Args:
        df: Input DataFrame.
        dependent_var: Dependent variable (y).
        key_var: Same as endogenous_var (the instrumented variable).
        control_vars: Exogenous control variables.
        endogenous_var: The endogenous explanatory variable.
        instruments: Instrument variables (at least 1).

    Returns:
        Dict with "baseline" and "diagnostics" keys.
        baseline includes stage1_f for instrument strength.
    """
    # Drop rows with any missing values (like Stata reg)
    _all_iv_vars = list(dict.fromkeys([dependent_var, endogenous_var] + instruments + control_vars))
    _model_data = df[_all_iv_vars].dropna()
    n_missing_dropped = len(df) - len(_model_data)
    df = df.loc[_model_data.index].copy()
    # Non-numeric column check
    _non_numeric = [col for col in _all_iv_vars if col != dependent_var and not pd.api.types.is_numeric_dtype(df[col])]
    if _non_numeric:
        raise ValueError(f"非数值类型变量不能参与回归: {chr(44).join(_non_numeric)}。请检查这些列是否包含文本数据。")

    # Stage 1
    model1, v_hat, f_stat = _run_stage1(df, endogenous_var, instruments, control_vars)

    # Stage 2
    model2, X2 = _run_stage2(df, dependent_var, endogenous_var, v_hat, control_vars)
    infl2 = model2.get_influence()

    key_idx = 1  # endogenous_var is first after constant in stage 2
    XtX_inv = np.linalg.inv(X2.values.T @ X2.values)
    XtX_inv_diag = np.diag(XtX_inv)

    baseline = {
        "beta": float(model2.params.iloc[key_idx]),
        "se": float(model2.bse.iloc[key_idx]),
        "t_stat": float(model2.tvalues.iloc[key_idx]),
        "p_value": float(model2.pvalues.iloc[key_idx]),
        "r_squared": float(model2.rsquared),
        "n_obs": int(model2.nobs),
        "df": int(model2.df_resid),
        "stage1_f": float(f_stat) if f_stat is not None else 0.0,
        "n_missing_dropped": n_missing_dropped,
    }

    diagnostics = {
        "hat_matrix_diag": infl2.hat_matrix_diag,
        "resid": model2.resid,
        "dfbetas": infl2.dfbetas,
        "sigma2_not_obsi": infl2.sigma2_not_obsi,
        "params_not_obsi": infl2.params_not_obsi,
        "X": X2,
        "XtX_inv_diag": XtX_inv_diag,
        "key_var_index": key_idx,
        "beta_vector": model2.params.values,
    }

    return {"baseline": baseline, "diagnostics": diagnostics}


def run_iv_greedy(
    df: pd.DataFrame,
    dependent_var: str,
    key_var: str,
    control_vars: list[str],
    endogenous_var: str,
    instruments: list[str],
    significance_threshold: float,
    max_deletions_pct: float,
    direction: str = "both",
) -> dict:
    """Greedy iterative deletion for 2SLS via CFA.

    Each iteration re-fits both stages (v_hat depends on stage-1 fit).
    Deletion priority based on stage-2 t-value. Stage-1 F tracked separately.

    Returns dict with baseline, deletion_path, final, spec_curves, f_curve.
    """
    n_total = len(df)
    max_deletions = int(n_total * max_deletions_pct / 100.0)
    df_remaining = df.copy()
    df_remaining["__orig_idx__"] = np.arange(n_total)

    result = fit_iv(df_remaining, dependent_var, key_var, control_vars, endogenous_var, instruments)
    baseline = result["baseline"]
    p_current = baseline["p_value"]
    t_current = baseline["t_stat"]
    beta_current = baseline["beta"]
    f_current = baseline["stage1_f"]

    spec_path = [{"n_del": 0, "t": round(t_current, 6)}]
    f_path = [{"n_del": 0, "f": round(f_current, 4)}]
    deletion_path = []
    deleted_orig_indices = []

    while p_current > significance_threshold and len(deleted_orig_indices) < max_deletions:
        diag = result["diagnostics"]
        t_del = compute_deletion_t_values(
            diag["params_not_obsi"],
            diag["sigma2_not_obsi"],
            diag["XtX_inv_diag"],
            diag["key_var_index"],
        )

        # Apply direction filter if needed
        if direction != "both":
            beta_del = diag["params_not_obsi"][:, diag["key_var_index"]]
            scores, phase_label = _apply_direction_filter(
                t_del=t_del, current_t=t_current,
                current_beta=beta_current, beta_del=beta_del,
                direction=direction,
            )
        else:
            scores = np.abs(t_del)
            phase_label = "none"

        best_idx = int(np.argmax(scores))

        if phase_label == "sign_flip":
            if scores[best_idx] <= 0.0:
                break
        else:
            t_best = float(t_del[best_idx])
            if abs(t_best) <= abs(t_current):
                break

        obs_orig_idx = int(df_remaining.iloc[best_idx]["__orig_idx__"])
        deleted_orig_indices.append(obs_orig_idx)

        df_remaining = df_remaining.drop(df_remaining.index[best_idx]).reset_index(drop=True)

        result = fit_iv(df_remaining, dependent_var, key_var, control_vars, endogenous_var, instruments)
        t_current = result["baseline"]["t_stat"]
        p_current = result["baseline"]["p_value"]
        beta_current = result["baseline"]["beta"]
        f_current = result["baseline"]["stage1_f"]

        step = len(deletion_path) + 1
        deletion_path.append({
            "step": step, "obs_id": int(obs_orig_idx),
            "t_after": round(float(t_current), 6),
            "p_after": round(float(p_current), 6),
            "direction": phase_label,
        })
        spec_path.append({"n_del": step, "t": round(float(t_current), 6)})
        f_path.append({"n_del": step, "f": round(float(f_current), 4)})

    final_result = fit_iv(df_remaining, dependent_var, key_var, control_vars, endogenous_var, instruments)
    fb = final_result["baseline"]

    if direction == "both":
        direction_achieved = "both"
    elif fb["beta"] >= 0:
        direction_achieved = "positive"
    else:
        direction_achieved = "negative"

    return {
        "baseline": {
            "beta": round(baseline["beta"], 6),
            "se": round(baseline["se"], 6),
            "t_stat": round(baseline["t_stat"], 6),
            "p_value": round(baseline["p_value"], 6),
            "r_squared": round(baseline["r_squared"], 6),
            "n_obs": baseline["n_obs"],
            "df": baseline["df"],
            "stage1_f": round(baseline["stage1_f"], 4),
        },
        "deletion_path": deletion_path,
        "final": {
            "beta": round(fb["beta"], 6),
            "se": round(fb["se"], 6),
            "t_stat": round(fb["t_stat"], 6),
            "p_value": round(fb["p_value"], 6),
            "r_squared": round(fb["r_squared"], 6),
            "deleted_obs": deleted_orig_indices,
            "n_deleted": len(deleted_orig_indices),
            "direction_achieved": direction_achieved,
            "stage1_f": round(fb["stage1_f"], 4),
        },
        "spec_curves": [{
            "control_set": " + ".join(control_vars),
            "path": spec_path,
        }],
        "f_curve": f_path,
    }

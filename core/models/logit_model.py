"""Logit / Probit model fitting and greedy deletion via statsmodels.

Uses one-step Newton approximation (Pregibon 1981) for diagnostics.
statsmodels get_influence().dfbetas returns standardized dfbetas
(units = standard error), so the approximate formula is:
    t_approx[i] = beta_j / bse_j - dfbetas[i, j]
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def fit_logit(
    df: pd.DataFrame,
    dependent_var: str,
    key_var: str,
    control_vars: list[str],
    model_type: str = "logit",
) -> dict:
    """Fit Logit or Probit model and extract baseline + diagnostics.

    Args:
        df: Input DataFrame.
        dependent_var: Binary dependent variable (0/1).
        key_var: Key explanatory variable.
        control_vars: Control variable column names.
        model_type: "logit" or "probit".

    Returns:
        Dict with keys "baseline" and "diagnostics".
        baseline format matches ols_model.fit_ols output.
    """
    all_vars = [key_var] + [v for v in control_vars if v != key_var]
    X = sm.add_constant(df[all_vars].copy())
    y = df[dependent_var].values

    ModelClass = sm.Logit if model_type == "logit" else sm.Probit
    model = ModelClass(y, X).fit(disp=0)
    infl = model.get_influence()

    key_idx = list(X.columns).index(key_var)

    # Pseudo R^2 (McFadden)
    null_model = ModelClass(y, np.ones((len(y), 1))).fit(disp=0)
    pseudo_r2 = 1 - model.llf / null_model.llf

    baseline = {
        "beta": float(model.params[key_var]),
        "se": float(model.bse[key_var]),
        "t_stat": float(model.tvalues[key_var]),
        "p_value": float(model.pvalues[key_var]),
        "r_squared": round(float(pseudo_r2), 6),
        "n_obs": int(model.nobs),
        "df": int(model.df_resid),
    }

    diagnostics = {
        "dfbetas": infl.dfbetas,
        "params": model.params.values,
        "bse": model.bse.values,
        "key_var_index": key_idx,
        "X": X.values,
    }

    return {"baseline": baseline, "diagnostics": diagnostics}


def _compute_logit_deletion_t(
    dfbetas: np.ndarray,
    beta_vector: np.ndarray,
    bse_vector: np.ndarray,
    key_var_index: int,
) -> np.ndarray:
    """Compute approximate post-deletion t-values for Logit/Probit.

    Uses the one-step Newton (Pregibon) approximation.
    statsmodels dfbetas are standardized: dfbetas[i,j] = (beta_j - beta^(i)_j) / bse_j.
    Therefore: t^(i)_j = beta_j / bse_j - dfbetas[i, j]

    Args:
        dfbetas: (N, K) standardized dfbetas from statsmodels get_influence().
        beta_vector: (K,) full-sample coefficient estimates.
        bse_vector: (K,) full-sample standard errors.
        key_var_index: Column index of the key variable.

    Returns:
        (N,) array of approximate post-deletion t-values.
    """
    beta_j = beta_vector[key_var_index]
    bse_j = bse_vector[key_var_index]
    # dfbetas are standardized: unit = standard error
    t_approx = beta_j / bse_j - dfbetas[:, key_var_index]
    return t_approx


def run_logit_greedy(
    df: pd.DataFrame,
    dependent_var: str,
    key_var: str,
    control_vars: list[str],
    significance_threshold: float,
    max_deletions_pct: float,
    model_type: str = "logit",
    exact: bool = False,
) -> dict:
    """Run greedy iterative deletion for a single Logit/Probit model.

    Args:
        df: Input DataFrame.
        dependent_var: Binary dependent variable (0/1).
        key_var: Key explanatory variable.
        control_vars: Control variable column names.
        significance_threshold: p-value threshold for stopping.
        max_deletions_pct: Max fraction of observations to delete (e.g. 5.0 = 5%).
        model_type: "logit" or "probit".
        exact: If True, refit full MLE each iteration. If False, use one-step approx.

    Returns:
        Dict with keys: baseline, deletion_path, final, spec_curves.
    """
    n_total = len(df)
    max_deletions = int(n_total * max_deletions_pct / 100.0)
    df_remaining = df.copy()
    df_remaining["__orig_idx__"] = np.arange(n_total)

    # Step 1: Baseline
    result = fit_logit(df_remaining, dependent_var, key_var, control_vars, model_type)
    baseline = result["baseline"]
    p_current = baseline["p_value"]
    t_current = baseline["t_stat"]

    spec_path = [{"n_del": 0, "t": round(t_current, 6)}]
    deletion_path = []
    deleted_orig_indices = []

    while p_current > significance_threshold and len(deleted_orig_indices) < max_deletions:
        diag = result["diagnostics"]

        if exact:
            # Exact mode: compute LOO t-values by refitting for each obs
            active_n = len(df_remaining)
            X = diag["X"]
            y = df_remaining[dependent_var].values
            key_idx = diag["key_var_index"]
            t_del = np.zeros(active_n)

            for i in range(active_n):
                mask = np.ones(active_n, dtype=bool)
                mask[i] = False
                ModelClass = sm.Logit if model_type == "logit" else sm.Probit
                try:
                    m_loo = ModelClass(y[mask], X[mask]).fit(disp=0)
                    t_del[i] = m_loo.tvalues[key_idx]
                except Exception:
                    t_del[i] = t_current  # fallback if MLE fails
        else:
            # Approximate mode: one-step Newton approximation
            t_del = _compute_logit_deletion_t(
                diag["dfbetas"],
                diag["params"],
                diag["bse"],
                diag["key_var_index"],
            )

        # Select observation with maximum |t|
        t_abs = np.abs(t_del)
        best_idx_in_remaining = int(np.argmax(t_abs))
        t_best = float(t_del[best_idx_in_remaining])

        # Check for improvement
        if abs(t_best) <= abs(t_current):
            break

        # Delete the observation
        obs_orig_idx = int(df_remaining.iloc[best_idx_in_remaining]["__orig_idx__"])
        deleted_orig_indices.append(obs_orig_idx)

        df_remaining = df_remaining.drop(df_remaining.index[best_idx_in_remaining]).reset_index(drop=True)

        # Refit
        result = fit_logit(df_remaining, dependent_var, key_var, control_vars, model_type)
        t_current = result["baseline"]["t_stat"]
        p_current = result["baseline"]["p_value"]

        # Record step
        step = len(deletion_path) + 1
        deletion_path.append({
            "step": step,
            "obs_id": int(obs_orig_idx),
            "t_after": round(float(t_current), 6),
            "p_after": round(float(p_current), 6),
        })
        spec_path.append({
            "n_del": step,
            "t": round(float(t_current), 6),
        })

    # Final status
    final_result = fit_logit(df_remaining, dependent_var, key_var, control_vars, model_type)
    fb = final_result["baseline"]

    return {
        "baseline": {
            "beta": round(baseline["beta"], 6),
            "se": round(baseline["se"], 6),
            "t_stat": round(baseline["t_stat"], 6),
            "p_value": round(baseline["p_value"], 6),
            "r_squared": round(baseline["r_squared"], 6),
            "n_obs": baseline["n_obs"],
            "df": baseline["df"],
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
        },
        "spec_curves": [
            {
                "control_set": " + ".join(control_vars),
                "path": spec_path,
            }
        ],
    }

"""Single-model greedy iterative deletion algorithm.

Algorithm (from technical doc 5.1):
  1. Fit baseline OLS, get current t and p.
  2. While p > threshold AND len(deleted) < max_deletions:
     a. Compute post-deletion t for each non-deleted observation.
     b. Select observation that maximizes post-deletion t.
     c. If no improvement possible, break.
     d. Delete the observation, refit OLS, record step.
  3. Return baseline, deletion_path, final status.
"""

import numpy as np
import pandas as pd

from core.models.ols_model import fit_ols
from core.influence import compute_deletion_t_values


def greedy_deletion(
    df: pd.DataFrame,
    dependent_var: str,
    key_var: str,
    control_vars: list[str],
    significance_threshold: float,
    max_deletions_pct: float,
) -> dict:
    """Run greedy iterative deletion for a single OLS model.

    Args:
        df: Input DataFrame.
        dependent_var: Dependent variable column name.
        key_var: Key explanatory variable (tracked through deletion).
        control_vars: Control variable column names.
        significance_threshold: p-value threshold for stopping (e.g. 0.05).
        max_deletions_pct: Max fraction of observations to delete (e.g. 5.0 = 5%).

    Returns:
        Dict with keys: baseline, deletion_path, final, spec_curves.
        Conforms to the single-model portion of compute_output.
    """
    n_total = len(df)
    max_deletions = int(n_total * max_deletions_pct / 100.0)
    df_remaining = df.copy()
    df_remaining["__orig_idx__"] = np.arange(n_total)

    # ── Step 1: Baseline regression
    result = fit_ols(df_remaining, dependent_var, key_var, control_vars)
    baseline = result["baseline"]
    p_current = baseline["p_value"]
    t_current = baseline["t_stat"]

    # ── Spec curve: record t at n_del=0
    spec_path = [{"n_del": 0, "t": round(t_current, 6)}]
    deletion_path = []
    deleted_orig_indices = []

    while p_current > significance_threshold and len(deleted_orig_indices) < max_deletions:
        diag = result["diagnostics"]
        active_n = len(df_remaining)
        active_mask = np.ones(active_n, dtype=bool)

        # Step 3a: Compute post-deletion t-values
        t_del = compute_deletion_t_values(
            diag["params_not_obsi"],
            diag["sigma2_not_obsi"],
            diag["XtX_inv_diag"],
            diag["key_var_index"],
        )

        # Step 3b: Select observation with maximum t
        # Use absolute t-value for ranking (we care about significance)
        t_abs = np.abs(t_del)
        best_idx_in_remaining = int(np.argmax(t_abs))
        t_best = float(t_del[best_idx_in_remaining])

        # Step 3c: Check for improvement
        if abs(t_best) <= abs(t_current):
            break  # No further improvement possible

        # Step 3d: Delete the observation
        obs_orig_idx = int(df_remaining.iloc[best_idx_in_remaining]["__orig_idx__"])
        deleted_orig_indices.append(obs_orig_idx)

        df_remaining = df_remaining.drop(df_remaining.index[best_idx_in_remaining]).reset_index(drop=True)

        # Step 3e: Refit OLS
        result = fit_ols(df_remaining, dependent_var, key_var, control_vars)
        t_current = result["baseline"]["t_stat"]
        p_current = result["baseline"]["p_value"]

        # Step 3f: Record step
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

    # ── Final status
    final_result = fit_ols(df_remaining, dependent_var, key_var, control_vars)
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

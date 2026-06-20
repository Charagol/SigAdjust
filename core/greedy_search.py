"""Single-model greedy iterative deletion algorithm.

Algorithm (from technical doc 5.1):
  1. Fit baseline OLS, get current t and p.
  2. While p > threshold AND len(deleted) < max_deletions:
     a. Compute post-deletion t for each non-deleted observation.
     b. Select observation that maximizes post-deletion t.
     c. If no improvement possible, break.
     d. Delete the observation, refit OLS, record step.
  3. Return baseline, deletion_path, final status.

Direction control (Batch 5):
  - "both": original behavior, no direction filtering.
  - "positive"/"negative": two-phase strategy.
    Phase 1 (sign_flip): if current beta sign differs from target, delete
      observations that move beta toward the target direction.
    Phase 2 (optimize): once sign matches, only keep candidates whose t-value
      improves in the target direction.
"""

import numpy as np
import pandas as pd

from core.models.ols_model import fit_ols
from core.influence import compute_deletion_t_values


def _apply_direction_filter(
    t_del: np.ndarray,
    current_t: float,
    current_beta: float,
    beta_del: np.ndarray,
    direction: str,
) -> tuple[np.ndarray, str]:
    """Apply direction-based filtering to candidate selection.

    Two-phase strategy:
    - Flip phase: current beta sign differs from target direction. Score by
      how much each candidate moves beta toward the target direction.
    - Optimize phase: sign matches. Score by |t_del|, but only keep candidates
      that improve t in the target direction.
    - Both mode: unchanged original behavior.

    Args:
        t_del: (N,) post-deletion t-values for remaining observations.
        current_t: Current t-value before deletion.
        current_beta: Current beta coefficient before deletion.
        beta_del: (N,) post-deletion beta for remaining observations.
        direction: "positive", "negative", or "both".

    Returns:
        Tuple of (scores, phase_label):
        - scores: selection scores (higher = better candidate).
        - phase_label: "default", "sign_flip", or "optimize".
    """
    if direction == "both":
        return np.abs(t_del), "default"

    target_positive = direction == "positive"
    sign_matches = (current_beta >= 0) == target_positive

    if sign_matches:
        # Optimization phase: sign matches target direction
        phase_label = "optimize"
        if target_positive:
            mask = t_del > current_t
        else:
            mask = t_del < current_t
        # Non-qualifying candidates score = |current_t|, won't be selected
        scores = np.where(mask, np.abs(t_del), np.abs(current_t))
        return scores, phase_label
    else:
        # Flip phase: sign differs from target direction
        phase_label = "sign_flip"
        delta = beta_del - current_beta if target_positive else current_beta - beta_del
        # delta > 0 means moving toward target direction
        scores = np.where(delta > 0, delta, 0.0)
        return scores, phase_label


def greedy_deletion(
    df: pd.DataFrame,
    dependent_var: str,
    key_var: str,
    control_vars: list[str],
    significance_threshold: float,
    max_deletions_pct: float,
    direction: str = "both",
) -> dict:
    """Run greedy iterative deletion for a single OLS model.

    Args:
        df: Input DataFrame.
        dependent_var: Dependent variable column name.
        key_var: Key explanatory variable (tracked through deletion).
        control_vars: Control variable column names.
        significance_threshold: p-value threshold for stopping (e.g. 0.05).
        max_deletions_pct: Max fraction of observations to delete (e.g. 5.0 = 5%).
        direction: Direction control: "positive", "negative", or "both".

    Returns:
        Dict with keys: baseline, deletion_path, final, spec_curves.
        Conforms to the single-model portion of compute_output.
    """
    n_total = len(df)
    max_deletions = int(n_total * max_deletions_pct / 100.0)
    df_remaining = df.copy()
    df_remaining["__orig_idx__"] = np.arange(n_total)

    # --- Step 1: Baseline regression ---
    result = fit_ols(df_remaining, dependent_var, key_var, control_vars)
    baseline = result["baseline"]
    p_current = baseline["p_value"]
    t_current = baseline["t_stat"]
    beta_current = baseline["beta"]

    # --- Spec curve: record t at n_del=0 ---
    spec_path = [{"n_del": 0, "t": round(t_current, 6)}]
    deletion_path = []
    deleted_orig_indices = []

    while p_current > significance_threshold and len(deleted_orig_indices) < max_deletions:
        diag = result["diagnostics"]

        # Step 3a: Compute post-deletion t-values
        t_del = compute_deletion_t_values(
            diag["params_not_obsi"],
            diag["sigma2_not_obsi"],
            diag["XtX_inv_diag"],
            diag["key_var_index"],
        )

        # Step 3b: Apply direction filter
        if direction != "both":
            beta_del = diag["params_not_obsi"][:, diag["key_var_index"]]
            scores, phase_label = _apply_direction_filter(
                t_del=t_del,
                current_t=t_current,
                current_beta=beta_current,
                beta_del=beta_del,
                direction=direction,
            )
        else:
            scores = np.abs(t_del)
            phase_label = "default"

        # Step 3c: Select best candidate
        best_idx_in_remaining = int(np.argmax(scores))

        if phase_label == "sign_flip":
            if scores[best_idx_in_remaining] <= 0.0:
                break  # No candidate moves beta in target direction
        else:
            # both or optimize — use original t-improvement check
            t_best = float(t_del[best_idx_in_remaining])
            if abs(t_best) <= abs(t_current):
                break

        # Step 3d: Delete the observation
        obs_orig_idx = int(df_remaining.iloc[best_idx_in_remaining]["__orig_idx__"])
        deleted_orig_indices.append(obs_orig_idx)

        df_remaining = df_remaining.drop(df_remaining.index[best_idx_in_remaining]).reset_index(drop=True)

        # Step 3e: Refit OLS
        result = fit_ols(df_remaining, dependent_var, key_var, control_vars)
        t_current = result["baseline"]["t_stat"]
        p_current = result["baseline"]["p_value"]
        beta_current = result["baseline"]["beta"]

        # Step 3f: Record step
        step = len(deletion_path) + 1
        deletion_path.append({
            "step": step,
            "obs_id": int(obs_orig_idx),
            "t_after": round(float(t_current), 6),
            "p_after": round(float(p_current), 6),
            "direction": phase_label,
        })
        spec_path.append({
            "n_del": step,
            "t": round(float(t_current), 6),
        })

    # --- Final status ---
    final_result = fit_ols(df_remaining, dependent_var, key_var, control_vars)
    fb = final_result["baseline"]

    # Determine direction_achieved for final output
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
        },
        "spec_curves": [
            {
                "control_set": " + ".join(control_vars),
                "path": spec_path,
            }
        ],
    }

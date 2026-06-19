"""Entry-point pipeline: compute_input -> full pipeline -> compute_output.

Orchestrates model-specific pipelines:
  OLS: greedy_deletion
  Logit/Probit: run_logit_greedy
  FE: run_fe_greedy
"""

import pandas as pd
from core.greedy_search import greedy_deletion


def run_pipeline(compute_input: dict) -> dict:
    """Run the full computation pipeline for all models.

    Args:
        compute_input: Dict conforming to compute_input contract (design-v1 4.2).

    Returns:
        Dict conforming to compute_output contract (design-v1 4.3).
    """
    df = compute_input["df"]
    settings = compute_input.get("global_settings", {})
    models_config = compute_input.get("models", [])

    significance_threshold = settings.get("significance_threshold", 0.05)
    max_deletions_pct = settings.get("max_deletions_pct", 5.0)

    results = {}

    for model_cfg in models_config:
        name = model_cfg["name"]
        model_type = model_cfg.get("type", "ols")
        target_p = model_cfg.get("target_p", significance_threshold)

        if model_type == "ols":
            result = greedy_deletion(
                df=df,
                dependent_var=model_cfg["dependent_var"],
                key_var=model_cfg["key_var"],
                control_vars=model_cfg.get("control_vars", []),
                significance_threshold=target_p,
                max_deletions_pct=max_deletions_pct,
            )
            results[name] = result
        elif model_type in ("logit", "probit"):
            from core.models.logit_model import run_logit_greedy
            result = run_logit_greedy(
                df=df,
                dependent_var=model_cfg["dependent_var"],
                key_var=model_cfg["key_var"],
                control_vars=model_cfg.get("control_vars", []),
                significance_threshold=target_p,
                max_deletions_pct=max_deletions_pct,
                model_type=model_type,
            )
            results[name] = result
        elif model_type == "iv":
            from core.models.iv_model import run_iv_greedy
            result = run_iv_greedy(
                df=df,
                dependent_var=model_cfg["dependent_var"],
                key_var=model_cfg["key_var"],
                control_vars=model_cfg.get("control_vars", []),
                endogenous_var=model_cfg.get("endogenous_var", model_cfg["key_var"]),
                instruments=model_cfg.get("instruments", []),
                significance_threshold=target_p,
                max_deletions_pct=max_deletions_pct,
            )
            results[name] = result
        elif model_type == "fe":
            from core.models.fe_model import run_fe_greedy
            result = run_fe_greedy(
                df=df,
                dependent_var=model_cfg["dependent_var"],
                key_var=model_cfg["key_var"],
                control_vars=model_cfg.get("control_vars", []),
                fe_vars=model_cfg.get("fe_vars", []),
                significance_threshold=target_p,
                max_deletions_pct=max_deletions_pct,
            )
            results[name] = result
        else:
            results[name] = {
                "baseline": None,
                "deletion_path": [],
                "final": None,
                "spec_curves": [],
            }

    multi = None
    if len(models_config) > 1:
        from core.multi_model import arbitrate
        multi = arbitrate(results, models_config, df)

    return {
        "models": results,
        "multi_model": multi,
    }

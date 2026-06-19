"""Entry-point pipeline: compute_input → full pipeline → compute_output.

Orchestrates the single-model OLS pipeline:
  spec_enum → ols_model → influence → greedy_search → output dict.
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
        else:
            # Placeholder for Phase 4+
            results[name] = {
                "baseline": None,
                "deletion_path": [],
                "final": None,
                "spec_curves": [],
            }

    return {
        "models": results,
        "multi_model": None,  # Placeholder for Phase 6
    }

"""Multi-model arbitration: safe intersection, conflict matrix, weighted greedy.

All functions pure -- no Streamlit dependency.
"""

import numpy as np
import pandas as pd
from core.models.ols_model import fit_ols


def _fit_model(df, cfg):
    mtype = cfg.get("type", "ols")
    dv = cfg["dependent_var"]
    kv = cfg["key_var"]
    cv = cfg.get("control_vars", [])
    if mtype == "ols":
        return fit_ols(df, dv, kv, cv)
    elif mtype in ("logit", "probit"):
        from core.models.logit_model import fit_logit
        return fit_logit(df, dv, kv, cv, model_type=mtype)
    elif mtype == "fe":
        from core.models.fe_model import fit_fe
        return fit_fe(df, dv, kv, cv, fe_vars=cfg.get("fe_vars", []))
    return fit_ols(df, dv, kv, cv)


def _deleted(mr):
    return mr.get("final", {}).get("deleted_obs", [])


def compute_safe_intersection(models_results):
    sets = [set(_deleted(r)) for r in models_results.values()]
    if not sets:
        return []
    return sorted(set.intersection(*sets))


def compute_conflict_coefficient(models_results):
    sets = [set(_deleted(r)) for r in models_results.values()]
    if not sets:
        return 0.0
    union = set.union(*sets)
    inter = set.intersection(*sets)
    if len(union) == 0:
        return 0.0
    return round(1.0 - len(inter) / len(union), 4)


def compute_conflict_matrix(models_results, df, models_config, safe_intersection):
    safe_set = set(safe_intersection)
    all_flagged = set()
    for r in models_results.values():
        all_flagged.update(_deleted(r))
    ambiguous = sorted(all_flagged - safe_set)
    if not ambiguous:
        return []
    baselines = {}
    for cfg in models_config:
        bl = _fit_model(df, cfg)
        baselines[cfg["name"]] = bl["baseline"]
    matrix = []
    for obs_id in ambiguous:
        if obs_id >= len(df):
            continue
        mask = np.ones(len(df), dtype=bool)
        mask[obs_id] = False
        df_sub = df.loc[mask].reset_index(drop=True)
        effects = {}
        for cfg in models_config:
            try:
                fit_sub = _fit_model(df_sub, cfg)
                t_after = fit_sub["baseline"]["t_stat"]
                t_before = baselines.get(cfg["name"], {}).get("t_stat", 0)
                effects[cfg["name"]] = round(t_after - t_before, 4)
            except Exception:
                effects[cfg["name"]] = 0.0
        matrix.append({"obs_id": int(obs_id), "effects": effects, "recommendation": None, "note": None})
    return matrix


def generate_recommendations(conflict_matrix, safe_intersection):
    result = []
    for entry in conflict_matrix:
        effects = entry["effects"]
        min_eff = min(effects.values()) if effects else 0.0
        if min_eff > 0:
            rec, note = "delete", "对所有模型有利"
        elif min_eff < -1.0:
            worst = min(effects, key=effects.get)
            rec, note = "block", f"严重有害 {worst} ({effects[worst]:.2f})"
        elif min_eff < -0.1:
            harmful = [k for k, v in effects.items() if v < -0.1]
            rec, note = "caution", f"对 {', '.join(harmful)} 有害"
        else:
            rec, note = "split", "cannot satisfy all models"
        entry["recommendation"] = rec
        entry["note"] = note
        result.append(entry)
    return result


def layered_relaxation(models_results, models_config, safe_intersection, max_rounds=3):
    unmet = []
    for cfg in models_config:
        mname = cfg["name"]
        p_after = models_results.get(mname, {}).get("final", {}).get("p_value", 1.0)
        target = cfg.get("target_p", 0.05)
        if p_after > target:
            unmet.append(cfg)
    if not unmet:
        return {"status": "all_passed", "relaxations": []}
    unmet_sorted = sorted(unmet, key=lambda c: c.get("priority", 1))
    relaxations = []
    for i, cfg in enumerate(unmet_sorted[:max_rounds]):
        old_t = cfg.get("target_p", 0.05)
        new_t = min(old_t * 2, 0.10)
        relaxations.append({"model": cfg["name"], "old_threshold": old_t, "new_threshold": new_t})
    return {"status": "partial", "relaxations": relaxations}


def weighted_greedy(models_results, models_config, df, safe_intersection, max_deletions_pct=5.0):
    max_del = int(len(df) * max_deletions_pct / 100.0)
    current_set = set(safe_intersection)
    all_flagged = set()
    for r in models_results.values():
        all_flagged.update(_deleted(r))
    candidates = sorted(all_flagged - current_set)
    if not candidates:
        return {"recommended": sorted(current_set), "cautious": [], "blocked": []}

    def score_fn(deleted_set):
        mask = ~df.index.isin(deleted_set)
        if mask.sum() < 10:
            return -1.0
        df_sub = df.loc[mask].reset_index(drop=True)
        s = 0.0
        for cfg in models_config:
            try:
                fit_sub = _fit_model(df_sub, cfg)
                t_val = abs(fit_sub["baseline"]["t_stat"])
                w = cfg.get("priority", 3)
                s += w * max(0.0, t_val - 1.96)
            except Exception:
                pass
        return s

    best_score = score_fn(current_set)
    best_set = set(current_set)
    path = []
    for _ in range(min(len(candidates), max_del - len(current_set))):
        best_c, best_sc = None, best_score
        for c in candidates:
            if c in best_set:
                continue
            sc = score_fn(best_set | {c})
            if sc > best_sc:
                best_sc, best_c = sc, c
        if best_c is None or best_sc <= best_score:
            break
        best_set.add(best_c)
        best_score = best_sc
        candidates.remove(best_c)
        path.append({"obs_id": int(best_c), "score": round(best_score, 4)})

    return {"recommended": sorted(best_set), "cautious": sorted(set(candidates) - set(safe_intersection)), "blocked": [], "path": path}


def arbitrate(models_results, models_config, df):
    safe = compute_safe_intersection(models_results)
    coeff = compute_conflict_coefficient(models_results)
    conflict = compute_conflict_matrix(models_results, df, models_config, safe)
    conflict = generate_recommendations(conflict, safe)
    wg = weighted_greedy(models_results, models_config, df, safe)
    status_by_model = {}
    for cfg in models_config:
        mname = cfg["name"]
        p_after = models_results.get(mname, {}).get("final", {}).get("p_value", 1.0)
        target = cfg.get("target_p", 0.05)
        status_by_model[mname] = {"target": f"p<{target}", "achieved": f"p={p_after:.4f}", "status": "passed" if p_after <= target else "not_passed"}
    return {"conflict_coefficient": coeff, "safe_intersection": safe, "conflict_matrix": conflict, "weighted_greedy": wg, "status_by_model": status_by_model}

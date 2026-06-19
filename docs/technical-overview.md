# SigAdjust V1.0 — Technical Overview

> Generated: 2026-06-20 | Tests: 48/48 | Status: Released

A one-page overview for anyone taking over the project.

---

## Architecture

```
Browser (Streamlit UI)
  |
  v
app.py  (entry point, st.navigation with 4 pages)
  |
  +-- ui/page_data.py     (Page 1: data import)
  +-- ui/page_setup.py    (Page 2: model configuration, 1-4 models)
  +-- ui/page_progress.py (Page 3: computation progress, threading)
  +-- ui/page_results.py  (Page 4: results display + export)
  |
  +-- core/pipeline.py    (orchestrator: compute_input -> compute_output)
       |
       +-- core/greedy_search.py  (OLS single-model greedy)
       +-- core/models/ols_model.py, logit_model.py, fe_model.py, iv_model.py
       +-- core/influence.py      (post-deletion t-value computation)
       +-- core/spec_enum.py      (control variable combinations)
       +-- core/multi_model.py    (safe intersection, conflict matrix, weighted greedy)
       +-- core/export.py         (CSV, DTA, Excel, HTML)
```

**Key constraint**: `core/` modules never import `streamlit`. All functions accept/return Python dicts, DataFrames, or bytes.

**State management**: All shared state flows through `st.session_state` (no database, no Redis):

| Key | Type | Writer | Reader |
|-----|------|--------|--------|
| `df` | `pd.DataFrame` | Page 1 | Pages 2, 4 |
| `columns_info` | `dict` | Page 1 | Page 2 |
| `config` | `dict` (compute_input) | Page 2 | Page 3 |
| `results` | `dict` (compute_output) | Page 3 | Page 4 |
| `export_df` | `pd.DataFrame` | Page 4 | Page 4 |
| `progress` | `dict` | Page 3 | Page 3 |

`compute_input` / `compute_output` contracts are defined in `docs/design-v1.md` sections 4.2-4.3.

## Module Inventory

### core/ (pure computation, no UI dependency)

| File | Lines | Responsibility |
|------|-------|---------------|
| `validation.py` | ~60 | Column existence/type checks, missing value stats |
| `spec_enum.py` | ~25 | `itertools.combinations` enumeration of control variable subsets |
| `models/ols_model.py` | ~80 | OLS fit + `OLSInfluence` diagnostics |
| `models/logit_model.py` | ~180 | Logit/Probit fit + one-step Newton approx. + exact MLE greedy |
| `models/fe_model.py` | ~200 | FWL demaining via `pyfixest.feols` + demeaned OLS diagnostics |
| `models/iv_model.py` | ~160 | CFA decomposition (dual OLS), stage-1 F tracking |
| `influence.py` | ~70 | Post-deletion t-value: `params_not_obsi / sqrt(sigma2 * XtX_inv)` |
| `greedy_search.py` | ~120 | Single-model OLS greedy iterative deletion loop |
| `multi_model.py` | ~200 | Safe intersection, conflict matrix, weighted greedy, layered relaxation |
| `pipeline.py` | ~90 | Entry point: routes model type to correct greedy function, calls `arbitrate` |
| `export.py` | ~120 | CSV, DTA (32-char truncation), Excel (2-sheet), HTML (self-contained) |

### ui/ (Streamlit pages)

| File | Phase | Functionality |
|------|-------|---------------|
| `page_data.py` | 1 | File upload (CSV/DTA/Excel), data preview, column info |
| `page_setup.py` | 2-7 | Multi-model form (up to 4), model type selector, FE/IV conditional fields |
| `page_progress.py` | 3 | Threading-based pipeline execution, progress bar/status |
| `page_results.py` | 3-8 | Single-model curves + deletion paths, multi-model heatmap/Pareto, 4-format export |
| `pages.py` | — | Shared page function references (avoids circular imports) |

### tests/ (48 tests)

```
test_validation.py    10 tests   (pure function coverage)
test_spec_enum.py      3 tests   (empty/single/multi control vars)
test_ols_model.py      2 tests   (contract validation)
test_influence.py      4 tests   (t-value formula correctness)
test_greedy_search.py  5 tests   (monotonicity, budget, uniqueness)
test_logit_model.py    6 tests   (fit + greedy + dfbetas interpretation)
test_fe_model.py       3 tests   (FWL beta = pyfixest beta)
test_multi_model.py   11 tests   (intersection, conflict, recommendations, arbitrate)
test_iv_model.py       4 tests   (CFA beta = IV2SLS beta, F tracking)
```

## Design-Implementation Deviations

Documented differences between the original technical spec and final implementation:

| Item | Spec | Implementation |
|------|------|----------------|
| 2SLS diagnostics | Brute-force LOO both stages | CFA-OLS with stage-2 `OLSInfluence` |
| Logit dfbetas units | Unspecified | Confirmed standardized (units = SE) via n=200 verification; formula: `t = beta/bse - dfbetas` |
| weighted_greedy threshold | Dynamic t-value threshold per model | Uses hardcoded `1.96` (p~0.05); should be derived from t-distribution with model df |
| FE demean | One-time or per-iteration? | Re-demands every greedy iteration (group means change after deletion) |
| spec_curves | One per control combination | Phase 1-8 implementation tracks per-iteration t-value; full spec curve enumeration deferred |

## Known Limitations

- **Greedy algorithm**: Stepwise optimal, not globally optimal. Deletion of k observations may not be the best k-subset.
- **CFA standard errors**: Omit first-stage sampling error. Sufficient for deletion ranking, insufficient for exact inference.
- **DTA column names**: Truncated to 32 characters with `_trunc` suffix. Chinese column names replaced with underscores. Use CSV/Excel for full name preservation.
- **2SLS instruments**: Must be valid (F > 10 recommended). Weak instruments are detected but not blocked.
- **Multi-model upper limit**: 4 models maximum; UI hard-coded constraint.
- **FE second-order effects**: FWL demean ignores that deleting an observation changes group means for other observations in the same group (O(1/T_i) effect).

## Development Workflow

```
1. Write test in tests/
2. Implement in core/
3. python -m pytest tests/ -q --ignore=tests/test_placeholder.py
4. Update docs/task-tracker.md
5. rm -f .git/index.lock && git add -A && git commit -m "feat: ..."
```

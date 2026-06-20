# SigAdjust V2.0  Technical Overview

> Generated: 2026-06-21 | Tests: 70/70 | Status: Released

A one-page overview for anyone taking over the project.

---

## Architecture

V2.0 replaces the Streamlit UI layer with PySide6 desktop widgets
while preserving the core/ computation layer entirely unchanged.

```
main.py  ->  QApplication
                 |
          MainWindow(QTabWidget, 4 tabs)
           |         |           |
      DataPage  SetupPage  ProgressPage  ResultsPage
           |         |           |            |
           +--- SigAdjustViewModel ----+   (Signal/Slot bridge)
                     |
                 core/ (unchanged, 49 tests)
```

Key architectural change: V1 used st.session_state for shared state and
threading.Thread for background computation (3 known bugs). V2 uses a
dedicated ViewModel class with Qt Signal/Slot for reactive UI updates
and QThread for sandboxed background computation.

## Module Inventory

### Entry / UI Layer (ui/)

| File | Responsibility |
|------|---------------|
| `main.py` | PySide6 entry point, creates QApplication and MainWindow |
| `ui/main_window.py` | MainWindow(QMainWindow) with QTabWidget (4 tabs) + global QSS |
| `ui/viewmodel.py` | SigAdjustViewModel — single source of truth, Signal/Slot bridge |
| `ui/widgets/page_data.py` | DataPage — file open (CSV/DTA/Excel), preview, column info |
| `ui/widgets/page_setup.py` | SetupPage — multi-model config, ModelCard, direction UI, Stata import |
| `ui/widgets/page_progress.py` | ComputationWorker(QThread) + ComputationProgressPage |
| `ui/widgets/page_results.py` | ResultsPage — t/F charts (Plotly), deletion path, export (4 formats) |
| `ui/widgets/variable_selector.py` | VariableSelector — tag-based search+select, FlowLayout, max_selection |
| `ui/widgets/stata_parser.py` | StataCommandParser — parse reg/logit/probit/reghdfe commands |

### Core Computation (core/)  all unchanged from V1

| File | Responsibility |
|------|---------------|
| `core/spec_enum.py` | Specification enumeration for robustness checks |
| `core/validation.py` | Input validation, missing value summary |
| `core/models/ols_model.py` | OLS fit + diagnostics via statsmodels OLSInfluence |
| `core/models/logit_model.py` | Logit/Probit fit + one-step Newton diagnostics |
| `core/models/fe_model.py` | Fixed effects via FWL demean + OLS |
| `core/models/iv_model.py` | 2SLS/IV via Control Function Approach + dual OLS |
| `core/influence.py` | Post-deletion t-value computation, DFBETA |
| `core/greedy_search.py` | Greedy deletion algorithm + direction filter |
| `core/pipeline.py` | Orchestrator: compute_input -> compute_output |
| `core/multi_model.py` | Multi-model arbitration: safe intersection, conflict matrix |
| `core/export.py` | 4-format export (CSV/DTA/Excel/HTML) + light DTA + multi CSV |

### Packaging

| File | Purpose |
|------|---------|
| `sigadjust.spec` | PyInstaller --onefile build config |
| `requirements.txt` | Python dependencies (PySide6, statsmodels, pandas, plotly, ...) |

## Data Contract

compute_input / compute_output contracts are UNCHANGED from V1.
See docs/design-v1.md sections 4.2-4.3 for the full specification.

V2 additions:
- `global_settings.direction`: "both" | "positive" | "negative"
- `final.direction_achieved`: final direction state from direction algorithm
- `deletion_path[].direction`: "default" | "sign_flip" | "optimize"  phase label

## Test Distribution (70 total)

| Area | Count | What |
|------|-------|------|
| core OLS / influence | 10 | fit_ols, diagnostics, deletion t-values |
| core greedy_search | 9 | greedy deletion + 4 direction tests |
| core logit/probit | 6 | fit_logit, dfbetas, greedy loop |
| core FE | 3 | fit_fe, pyfixest comparison, greedy loop |
| core IV | 4 | CFA equivalence, fit_iv, greedy loop |
| core multi_model | 11 | conflict matrix, arbitration logic |
| core export | 5 | order column, light DTA, merge cmd |
| core validation | 8 | column check, type check, missing summary |
| core spec_enum | 3 | specification enumeration |
| ViewModel | 4 | load_data, signal emission |
| StataParser | 7 | 5 command types, factor vars, error cases |
| placeholder | 1 | import check |

## Technology Decisions (V2)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI Framework | PySide6 (not PyQt6) | LGPL license, commercial-friendly, official recommendation |
| Packaging | PyInstaller --onefile | Mature, single .exe distribution |
| Architecture | ViewModel + Signal/Slot | Keeps core/ pure, UI testable, V1 data contract intact |
| Background computation | QThread + Signal (not concurrent.futures) | Qt-native threading, natural Signal/Slot integration |
| Charts | Plotly (same as V1) | Interactive quality, embeddable via QWebEngineView |
| Config persistence | JSON (not pickle/TOML) | Human-readable, cross-platform, version-controllable |
| Stata parser | Regex-based (5 commands) | Phase 1 scope defined, no heavy parser needed |
| Direction algorithm | Two-phase (sign_flip -> optimize) | Explainable behavior, user-predictable, compatible with greedy |
| Variable selector | Custom QWidget (tags + search + grid) | Click-target variable names, no checkboxes, mutual exclusion |

## Design-Implementation Deviations

| Item | Spec | Implementation |
|:-----|:-----|:---------------|
| Weighted greedy | 1.96 hardcoded | Needed improvement but lower priority |
| FE each iteration | Re-demean each iteration | Kept current behavior |
| Setting curve enumeration | Full enumeration | Deferred to V3 |
| UI framework (V2) | PySide6 | Replaced Streamlit, full Chinese UI |
| Direction control (V2) | Two-phase (sign_flip -> optimize) | _apply_direction_filter helper function |
| Value label (V2) | No special handling | DTA files loaded with convert_categoricals=False |
| XY selection (V2) | Y single, X up to 2 | VariableSelector max_selection property |
| NaN handling (V2) | Stata-like dropna | Added to all 4 model fit functions |
| Non-numeric detection (V2) | Clear Chinese error message | Added to all 4 model fit functions |

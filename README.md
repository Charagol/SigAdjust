# SigAdjust — Statistical Significance Adjustment Tool

One-click regression diagnostics and sample optimization for econometric research.

## Installation

```bash
pip install -r requirements.txt
python main.py
```

## Usage

1. **Data Import** — Upload CSV, Stata DTA, or Excel files.
2. **Model Setup** — Configure 1-4 regression models (OLS, Logit, Probit, FE, 2SLS).
3. **Computation** — Greedy iterative deletion of outlier observations.
4. **Results** — Interactive t-value curves, deletion paths, and multi-model conflict analysis.

## Supported Models

| Model | Diagnostics | Method |
|-------|-------------|--------|
| OLS | DFBETA exact | `statsmodels.OLS.get_influence()` |
| Logit / Probit | One-step Newton approx. + exact MLE option | `statsmodels.Logit/Probit.get_influence()` |
| FE (Fixed Effects) | FWL demean + OLS | `pyfixest.feols` |
| 2SLS / IV | CFA decomposition (dual OLS) | `statsmodels.OLS` |

## Export Formats

- **CSV** — Raw data + drop flags
- **DTA** — Stata format (column names truncated to 32 chars)
- **Excel** — Two sheets: data + diagnostics
- **HTML** — Self-contained report with embedded Plotly charts

## Notes

- This tool performs statistical computation only. It does not replace causal identification.
- The greedy deletion algorithm is stepwise optimal but does not guarantee the globally optimal deletion subset.
- CFA-OLS standard errors omit first-stage sampling error. Sufficient for deletion ranking.
- DTA export truncates column names to 32 characters. Use CSV/Excel to preserve full names.

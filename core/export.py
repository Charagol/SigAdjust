"""Export utilities: CSV, DTA, Excel, HTML report generation.

All functions are pure — no Streamlit dependency.
Accept DataFrame + metadata, return bytes.
"""

import io
import pandas as pd
import numpy as np


def _sanitize_col(name, max_len=32):
    """Sanitize column name for DTA format (max 32 chars, alphanumeric + underscore)."""
    clean = "".join(c if c.isalnum() or c == "_" else "_" for c in str(name))
    clean = clean.strip("_") or "col"
    if len(clean) > max_len:
        clean = clean[:28] + "_trunc"
    return clean


def export_csv(df, deleted_obs, model_name):
    """Export CSV with drop_{model_name} flag column."""
    out = df.copy()
    col = _sanitize_col(f"drop_{model_name}")
    out[col] = 0
    for oid in deleted_obs:
        if oid < len(out):
            out.iloc[oid, out.columns.get_loc(col)] = 1
    return out.to_csv(index=False).encode("utf-8")


def export_dta(df, deleted_obs, model_name):
    """Export DTA format. Column names truncated to 32 chars."""
    out = df.copy()
    col = _sanitize_col(f"drop_{model_name}")
    out[col] = 0
    for oid in deleted_obs:
        if oid < len(out):
            out.iloc[oid, out.columns.get_loc(col)] = 1
    safe_cols = {c: _sanitize_col(c) for c in out.columns}
    out = out.rename(columns=safe_cols)
    buf = io.BytesIO()
    import pyreadstat
    pyreadstat.write_dta(out, buf)
    return buf.getvalue()


def export_excel(df, deleted_obs, model_name, baseline=None, deletion_path=None):
    """Export Excel with two sheets: data + diagnostic summary."""
    out = df.copy()
    col = f"drop_{model_name}".replace(" ", "_")
    out[col] = 0
    for oid in deleted_obs:
        if oid < len(out):
            out.iloc[oid, out.columns.get_loc(col)] = 1

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="data", index=False)
        if baseline or deletion_path:
            summary_rows = []
            if baseline:
                summary_rows.append(pd.DataFrame([baseline]))
            if deletion_path:
                summary_rows.append(pd.DataFrame(deletion_path))
            if summary_rows:
                summary = pd.concat(summary_rows, axis=0, ignore_index=True)
                summary.to_excel(writer, sheet_name="diagnostics", index=False)
    return buf.getvalue()


def export_html(df, deleted_obs, model_name, figures=None, baseline=None, deletion_path=None, conflict_matrix=None):
    """Self-contained HTML report with embedded Plotly charts."""
    import plotly.io as pio
    out = df.copy()
    col = f"drop_{model_name}".replace(" ", "_")
    out[col] = 0
    for oid in deleted_obs:
        if oid < len(out):
            out.iloc[oid, out.columns.get_loc(col)] = 1

    html_parts = ["<html><head><meta charset='utf-8'><title>SigAdjust Report</title>"]
    html_parts.append("<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>")
    html_parts.append("<style>body{font-family:sans-serif;margin:20px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}</style></head><body>")
    html_parts.append("<h1>SigAdjust Diagnostic Report</h1>")

    if baseline:
        html_parts.append("<h2>Baseline</h2>")
        html_parts.append(pd.DataFrame([baseline]).to_html(index=False))

    if deletion_path:
        html_parts.append("<h2>Deletion Path</h2>")
        html_parts.append(pd.DataFrame(deletion_path).to_html(index=False))

    if figures:
        for i, fig in enumerate(figures):
            html_parts.append(f"<h2>Figure {i+1}</h2>")
            html_parts.append(pio.to_html(fig, include_plotlyjs=False, full_html=False))

    if conflict_matrix:
        html_parts.append("<h2>Conflict Matrix</h2>")
        html_parts.append(pd.DataFrame(conflict_matrix).to_html(index=False))

    html_parts.append("<h2>Data Preview</h2>")
    html_parts.append(out.head(20).to_html(index=False))
    html_parts.append("</body></html>")

    return "\n".join(html_parts).encode("utf-8")


def export_multi_csv(df, safe_intersection):
    """Export CSV for multi-model: raw data + drop_all_safe column."""
    out = df.copy()
    out["drop_all_safe"] = 0
    for oid in safe_intersection:
        if oid < len(out):
            out.iloc[oid, out.columns.get_loc("drop_all_safe")] = 1
    return out.to_csv(index=False).encode("utf-8")

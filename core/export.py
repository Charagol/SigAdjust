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


def _build_drop_df(df, deleted_obs, model_name):
    """Build DataFrame with drop_{name} and drop_{name}_order columns."""
    out = df.copy()
    col = _sanitize_col(f"drop_{model_name}")
    out[col] = 0
    out[f"{col}_order"] = 0
    for order, oid in enumerate(deleted_obs, 1):
        if oid < len(out):
            out.iloc[oid, out.columns.get_loc(col)] = 1
            out.iloc[oid, out.columns.get_loc(f"{col}_order")] = order
    return out


def export_full_csv(df, deleted_obs, model_name):
    """Export CSV with drop flag and order column."""
    out = _build_drop_df(df, deleted_obs, model_name)
    return out.to_csv(index=False).encode("utf-8")


def export_full_dta(df, deleted_obs, model_name):
    """Export DTA with drop flag and order column."""
    out = _build_drop_df(df, deleted_obs, model_name)
    safe_cols = {c: _sanitize_col(c) for c in out.columns}
    out = out.rename(columns=safe_cols)
    buf = io.BytesIO()
    import pyreadstat
    pyreadstat.write_dta(out, buf)
    return buf.getvalue()


def export_full_excel(df, deleted_obs, model_name, baseline=None, deletion_path=None):
    """Export Excel with data + diagnostics sheets, includes order column."""
    out = _build_drop_df(df, deleted_obs, model_name)
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


def export_full_html(df, deleted_obs, model_name, figures=None, baseline=None, deletion_path=None, conflict_matrix=None):
    """Self-contained HTML report with order column and embedded charts."""
    import plotly.io as pio
    out = _build_drop_df(df, deleted_obs, model_name)
    html_parts = ['<html><head><meta charset="utf-8"><title>SigAdjust Report</title>']
    html_parts.append('<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>')
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
    col = _sanitize_col(f"drop_{model_name}")
    html_parts.append(out[[c for c in out.columns if c in [col, f"{col}_order"]]].head(20).to_html(index=False))
    html_parts.append("</body></html>")
    return "\n".join(html_parts).encode("utf-8")


def export_light_dta(df, deleted_obs, model_name, id_vars, output_path):
    import os, getpass
    """Export lightweight DTA (only id vars + drop columns) and return merge command.

    Returns:
        str: Stata merge command string.
    """
    out = _build_drop_df(df, deleted_obs, model_name)
    col = _sanitize_col(f"drop_{model_name}")
    keep_cols = [c for c in id_vars if c in out.columns]
    keep_cols.extend([col, f"{col}_order"])
    light = out[keep_cols]
    safe_cols = {c: _sanitize_col(c) for c in light.columns}
    light = light.rename(columns=safe_cols)
    light.to_stata(output_path, write_index=False)
    username = getpass.getuser()
    fname = os.path.basename(output_path)
    id_str = " ".join(id_vars)
    col_safe = _sanitize_col(col)
    merge_cmd = (
        f'merge 1:1 {id_str} using "C:\\\\Users\\\\{username}\\\\Downloads\\\\{fname}", '
        f"keepusing({col_safe}) nogen"
    )
    return merge_cmd


def export_multi_csv_full(df, safe_intersection, multi_model_names):
    """Export multi-model CSV with per-model drop flags and safe intersection."""
    out = df.copy()
    out["drop_all_safe"] = 0
    for oid in safe_intersection:
        if oid < len(out):
            out.iloc[oid, out.columns.get_loc("drop_all_safe")] = 1
    return out.to_csv(index=False).encode("utf-8")


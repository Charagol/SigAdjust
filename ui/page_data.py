"""Page 1: Data import — file upload, preview, and column diagnostics."""

import tempfile
import os
import streamlit as st
import pandas as pd
import pyreadstat

from core.validation import get_missing_summary


# ── File parsing helpers ──────────────────────────────────────────────

def _load_file(uploaded_file, ext: str) -> pd.DataFrame | None:
    """Parse an uploaded file into a DataFrame based on extension."""
    try:
        if ext == "csv":
            return pd.read_csv(uploaded_file)
        elif ext == "xlsx":
            return pd.read_excel(uploaded_file)
        elif ext == "dta":
            # pyreadstat needs a file path; save to temp file
            with tempfile.NamedTemporaryFile(suffix=".dta", delete=False) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            df, _meta = pyreadstat.read_dta(tmp_path)
            os.unlink(tmp_path)
            return df
    except Exception as e:
        st.error(f"文件解析失败: {e}")
    return None


# ── Page entry point ──────────────────────────────────────────────────

def page_data():
    """Data import page — file upload, preview, and column diagnostics."""
    st.title("数据导入")

    # ── File uploader
    uploaded_file = st.file_uploader(
        "上传数据文件",
        type=["csv", "dta", "xlsx"],
        help="支持 CSV / Stata DTA / Excel 格式",
    )

    if uploaded_file is None:
        st.info("请上传 CSV、DTA 或 Excel 格式的数据文件。")
        return

    # Clear previous data on new upload
    if "uploaded_filename" not in st.session_state:
        st.session_state.uploaded_filename = None

    if uploaded_file.name != st.session_state.uploaded_filename:
        for key in ("df", "columns_info"):
            st.session_state.pop(key, None)
        st.session_state.uploaded_filename = uploaded_file.name

    # ── Parse file
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    df = _load_file(uploaded_file, ext)

    if df is None or df.empty:
        return

    # ── Store in session_state
    st.session_state.df = df
    summary = get_missing_summary(df)
    st.session_state.columns_info = summary

    # ── Metrics row
    n_rows, n_cols = summary["n_rows"], summary["n_cols"]

    # Find column with highest missing rate
    worst_col = "—"
    worst_rate = 0.0
    for col_name, info in summary["columns"].items():
        if info["missing_rate"] > worst_rate:
            worst_rate = info["missing_rate"]
            worst_col = col_name

    c1, c2, c3 = st.columns(3)
    c1.metric("总行数", f"{n_rows:,}")
    c2.metric("总列数", n_cols)
    c3.metric(
        "最高缺失率",
        f"{worst_rate:.1%}",
        delta=worst_col if worst_col != "—" else None,
    )

    # ── Data preview
    st.subheader("数据预览 (前 20 行)")
    st.dataframe(df.head(20), use_container_width=True)

    # ── Column info table
    with st.expander("列信息详情"):
        col_data = []
        for col_name, info in summary["columns"].items():
            col_data.append({
                "列名": col_name,
                "类型": info["dtype"],
                "缺失数": info["n_missing"],
                "缺失率": f"{info['missing_rate']:.2%}",
            })
        st.dataframe(
            pd.DataFrame(col_data),
            use_container_width=True,
            hide_index=True,
        )

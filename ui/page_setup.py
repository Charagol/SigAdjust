"""Page 2: Model setup — configure OLS regression model."""

import streamlit as st
from core.spec_enum import generate_specs
from ui.pages import page_progress


def page_setup():
    """Model configuration page. Builds compute_input and launches analysis."""
    st.title("模型设定")

    # ── Guard: data must be loaded first
    if "df" not in st.session_state or st.session_state.df is None:
        st.warning("请先在 **数据导入** 页面上传数据文件。")
        return

    df = st.session_state.df
    col_names = list(df.columns)
    columns_detail = st.session_state.get("columns_info", {}).get("columns", {})

    # Numeric columns preferred for regression vars
    numeric_cols = [
        c for c in col_names
        if "float" in columns_detail.get(c, {}).get("dtype", "")
        or "int" in columns_detail.get(c, {}).get("dtype", "")
    ]
    if not numeric_cols:
        numeric_cols = col_names

    # ── Global settings ───────────────────────────────────────────────
    st.subheader("全局设置")

    c1, c2 = st.columns(2)
    with c1:
        p_threshold = st.number_input(
            "显著性阈值 (p)",
            value=0.05,
            min_value=0.001,
            max_value=0.50,
            step=0.01,
            help="当关键变量的 p 值降至该阈值以下时停止删除。",
        )
    with c2:
        max_pct = st.number_input(
            "最大删除比例 (%)",
            value=5.0,
            min_value=0.1,
            max_value=50.0,
            step=0.5,
            help="最多删除百分之多少的观测值。",
        )

    # ── Model configuration ───────────────────────────────────────────
    st.subheader("模型配置")

    model_name = st.text_input("模型名称", value="主回归")
    dependent_var = st.selectbox("被解释变量 (Y)", numeric_cols)
    key_var = st.selectbox("核心解释变量 (Key X)", numeric_cols)
    control_vars = st.multiselect(
        "控制变量",
        [c for c in col_names if c not in [dependent_var, key_var]],
    )

    if control_vars:
        n_combos = 2 ** len(control_vars) - 1
        st.caption(
            f"控制变量组合数: {n_combos} "
            f"(2^{len(control_vars)} - 1 种非空子集)"
        )

    # ── Launch ────────────────────────────────────────────────────────
    st.divider()

    if st.button("开始分析", type="primary", use_container_width=True):
        if not dependent_var or not key_var:
            st.error("请选择被解释变量和核心解释变量。")
            return

        config = {
            "df": df,
            "global_settings": {
                "significance_threshold": p_threshold,
                "max_deletions_pct": max_pct,
                "mode": "greedy",
            },
            "models": [
                {
                    "name": model_name,
                    "type": "ols",
                    "priority": 5,
                    "target_p": p_threshold,
                    "dependent_var": dependent_var,
                    "key_var": key_var,
                    "control_vars": control_vars,
                }
            ],
        }
        st.session_state.config = config
        st.session_state.results = None
        st.session_state._compute_started = False
        st.switch_page(page_progress)

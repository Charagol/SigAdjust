"""Page 2: Model setup -- multi-model configuration (up to 4 models)."""

import streamlit as st
from core.spec_enum import generate_specs
from ui.pages import page_progress


def page_setup():
    st.title("模型设定")

    if "df" not in st.session_state or st.session_state.df is None:
        st.warning("请先在数据导入页面上传数据文件。")
        return

    df = st.session_state.df
    col_names = list(df.columns)
    columns_detail = st.session_state.get("columns_info", {}).get("columns", {})
    numeric_cols = [c for c in col_names if "float" in columns_detail.get(c, {}).get("dtype", "") or "int" in columns_detail.get(c, {}).get("dtype", "")]
    if not numeric_cols:
        numeric_cols = col_names

    st.subheader("全局设置")
    c1, c2 = st.columns(2)
    with c1:
        p_threshold = st.number_input("显著性阈值 p", value=0.05, min_value=0.001, max_value=0.50, step=0.01)
    with c2:
        max_pct = st.number_input("最大删除比例 %", value=5.0, min_value=0.1, max_value=50.0, step=0.5)

    st.subheader("模型配置")
    if "model_count" not in st.session_state:
        st.session_state.model_count = 1

    c_add, _ = st.columns([2, 8])
    if st.session_state.model_count < 4:
        if c_add.button("+ 添加模型", help="最多 4 个模型"):
            st.session_state.model_count += 1
            st.rerun()

    models_config = []
    type_map = {"OLS": "ols", "Logit": "logit", "Probit": "probit", "FE (固定效应)": "fe", "2SLS": "iv"}
    total_combos = 0

    for i in range(st.session_state.model_count):
        with st.expander(f"模型 {i+1}", expanded=(i == 0)):
            mname = st.text_input(f"名称", value=f"模型_{i+1}", key=f"mname_{i}")
            mtype = st.selectbox(f"类型", ["OLS", "Logit", "Probit", "FE (固定效应)"], key=f"mtype_{i}")
            dv = st.selectbox(f"被解释变量", numeric_cols, key=f"dv_{i}")
            kv = st.selectbox(f"核心解释变量", numeric_cols, key=f"kv_{i}")
            cv = st.multiselect(f"控制变量", [c for c in col_names if c not in [dv, kv]], key=f"cv_{i}")
            fv = []
            ev = ""
            iv_list = []
            if mtype == "FE (固定效应)":
                fv = st.multiselect(f"固定效应变量", [c for c in col_names if c not in [dv, kv] + cv], key=f"fv_{i}")
            if mtype == "2SLS":
                ev = st.selectbox(f"内生变量", numeric_cols, key=f"ev_{i}")
                iv_list = st.multiselect(f"工具变量 (至少1个)", [c for c in col_names if c not in [dv, ev] + cv], key=f"iv_{i}")
            pri = st.slider("优先级", 1, 5, 5, key=f"pri_{i}", help="5=最高优先级")
            tp = st.number_input(f"目标 p 值", value=p_threshold, min_value=0.001, max_value=0.50, step=0.01, key=f"tp_{i}")

            models_config.append({"name": mname, "type": type_map[mtype], "priority": pri, "target_p": tp, "dependent_var": dv, "key_var": kv, "control_vars": cv, "fe_vars": fv, "endogenous_var": ev, "instruments": iv_list})
            if cv:
                total_combos += 2 ** len(cv) - 1

    if total_combos > 0:
        st.caption(f"控制变量组合总数: {total_combos}")

    st.divider()
    if st.button("开始分析", type="primary", use_container_width=True):
        for i, mc in enumerate(models_config):
            if not mc["dependent_var"] or not mc["key_var"]:
                st.error(f"模型 {i+1}: 请选择被解释变量和核心解释变量。")
                return
        config = {"df": df, "global_settings": {"significance_threshold": p_threshold, "max_deletions_pct": max_pct, "mode": "greedy"}, "models": models_config}
        st.session_state.config = config
        st.session_state.results = None
        st.session_state._compute_started = False
        st.switch_page(page_progress)

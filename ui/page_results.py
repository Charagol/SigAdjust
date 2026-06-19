"""Page 4: Results display — baseline vs adjusted metrics, charts, export."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def page_results():
    """Results display page. Shows t-value curves, deletion path, and export."""
    st.title("结果展示")

    if "results" not in st.session_state or st.session_state.results is None:
        st.warning("尚无计算结果。请先在 **模型设定** 页面启动分析。")
        return

    results = st.session_state.results
    config = st.session_state.config
    models = results.get("models", {})

    if not models:
        st.info("当前没有模型结果。")
        return

    # ── Show results for the first model (single-model for now)
    model_name = list(models.keys())[0]
    model_result = models[model_name]

    baseline = model_result.get("baseline", {})
    final = model_result.get("final", {})
    deletion_path = model_result.get("deletion_path", [])
    spec_curves = model_result.get("spec_curves", [])

    # ── Summary metrics ───────────────────────────────────────────────
    st.subheader("摘要")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("基线 t 值", f"{baseline.get('t_stat', 0):.4f}",
              delta=f"{final.get('t_stat', 0):.4f}" if final else None)
    c2.metric("基线 p 值", f"{baseline.get('p_value', 0):.4f}",
              delta=f"{final.get('p_value', 0):.4f}" if final else None,
              delta_color="inverse")
    c3.metric("R²", f"{baseline.get('r_squared', 0):.4f}",
              delta=f"{final.get('r_squared', 0):.4f}" if final else None)
    c4.metric("删除观测值", f"{final.get('n_deleted', 0)}", delta=None)

    # ── t-value curve ─────────────────────────────────────────────────
    if spec_curves:
        st.subheader("t 值变化曲线")
        threshold = config.get("global_settings", {}).get("significance_threshold", 0.05)

        fig = go.Figure()

        for curve in spec_curves:
            path = curve.get("path", [])
            n_del = [p["n_del"] for p in path]
            t_vals = [abs(p["t"]) for p in path]

            fig.add_trace(go.Scatter(
                x=n_del,
                y=t_vals,
                mode="lines+markers",
                name=curve.get("control_set", ""),
            ))

        # Horizontal threshold line (approximate — exact depends on df)
        fig.add_hline(
            y=1.96,
            line_dash="dash",
            line_color="red",
            annotation_text="p≈0.05",
        )

        fig.update_layout(
            xaxis_title="删除数量",
            yaxis_title="|t 值|",
            hovermode="x unified",
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    # ── Deletion path table ───────────────────────────────────────────
    if deletion_path:
        st.subheader("删除路径")
        path_df = pd.DataFrame(deletion_path)
        st.dataframe(path_df, use_container_width=True, hide_index=True)

    # ── Export ────────────────────────────────────────────────────────
    if final and final.get("deleted_obs"):
        st.subheader("导出")

        df = st.session_state.df.copy()
        model_name_clean = model_name.replace(" ", "_").replace("/", "_")
        drop_col = f"drop_{model_name_clean}"

        # Build drop flag column
        df[drop_col] = 0
        for obs_id in final["deleted_obs"]:
            if obs_id < len(df):
                df.iloc[obs_id, df.columns.get_loc(drop_col)] = 1

        st.session_state.export_df = df

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"下载 CSV ({len(df)} 行, {df.shape[1]} 列)",
            data=csv_data,
            file_name=f"sigadjust_{model_name_clean}.csv",
            mime="text/csv",
        )

        st.caption(f"已添加标识符列 `{drop_col}`: 1 = 建议删除, 0 = 保留")

"""Page 4: Results display -- single-model + multi-model analysis."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from core.export import export_csv, export_dta, export_excel, export_html, export_multi_csv


def page_results():
    st.title("结果展示")

    if "results" not in st.session_state or st.session_state.results is None:
        st.warning("尚无计算结果。请先在模型设定页面启动分析。")
        return

    results = st.session_state.results
    config = st.session_state.config
    models = results.get("models", {})
    multi = results.get("multi_model")

    if not models:
        st.info("当前没有模型结果。")
        return

    tabs = ["单模型结果"]
    if multi:
        tabs.append("多模型联动")

    tab_objs = st.tabs(tabs)

    # ── Tab 1: Single-model results ───────────────────────────────────
    with tab_objs[0]:
        for model_name, model_result in models.items():
            if not model_result or not model_result.get("baseline"):
                continue
            st.subheader(model_name)
            baseline = model_result.get("baseline", {})
            final = model_result.get("final", {})
            deletion_path = model_result.get("deletion_path", [])
            spec_curves = model_result.get("spec_curves", [])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("基线 t 值", f"{baseline.get('t_stat', 0):.4f}", delta=f"{final.get('t_stat', 0):.4f}" if final else None)
            c2.metric("基线 p 值", f"{baseline.get('p_value', 0):.4f}", delta=f"{final.get('p_value', 0):.4f}" if final else None, delta_color="inverse")
            c3.metric("R²", f"{baseline.get('r_squared', 0):.4f}", delta=f"{final.get('r_squared', 0):.4f}" if final else None)
            c4.metric("删除观测值", f"{final.get('n_deleted', 0)}", delta=None)

            if spec_curves:
                fig = go.Figure()
                for curve in spec_curves:
                    path = curve.get("path", [])
                    n_del = [p["n_del"] for p in path]
                    t_vals = [abs(p["t"]) for p in path]
                    fig.add_trace(go.Scatter(x=n_del, y=t_vals, mode="lines+markers", name=curve.get("control_set", "")))
                fig.add_hline(y=1.96, line_dash="dash", line_color="red", annotation_text="p≈0.05")
                fig.update_layout(xaxis_title="删除数量", yaxis_title="|t 值|", hovermode="x unified", height=350)
                st.plotly_chart(fig, use_container_width=True)

            f_curve = model_result.get("f_curve")
            if f_curve:
                st.caption("第一阶段 F 统计量 (工具强度)")
                fig_f = go.Figure()
                ndf = [p["n_del"] for p in f_curve]
                fv = [p["f"] for p in f_curve]
                fig_f.add_trace(go.Scatter(x=ndf, y=fv, mode="lines+markers", name="F"))
                fig_f.add_hline(y=10, line_dash="dash", line_color="orange", annotation_text="F=10")
                fig_f.update_layout(xaxis_title="删除数量", yaxis_title="F 统计量", height=250)
                st.plotly_chart(fig_f, use_container_width=True)

            if deletion_path:
                st.dataframe(pd.DataFrame(deletion_path), use_container_width=True, hide_index=True)

            if final and final.get("deleted_obs"):
                deleted = final.get("deleted_obs", [])
                mc = model_name.replace(" ", "_").replace("/", "_")
                raw = st.session_state.df.copy()
                ec1, ec2, ec3, ec4 = st.columns(4)
                ec1.download_button("下载 CSV", export_csv(raw, deleted, model_name), f"sigadjust_{mc}.csv", "text/csv")
                ec2.download_button("下载 DTA", export_dta(raw, deleted, model_name), f"sigadjust_{mc}.dta", "application/octet-stream")
                ec3.download_button("下载 Excel", export_excel(raw, deleted, model_name, baseline, deletion_path), f"sigadjust_{mc}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                ec4.download_button("下载 HTML", export_html(raw, deleted, model_name, [], baseline, deletion_path), f"sigadjust_{mc}.html", "text/html")

    # ── Tab 2: Multi-model analysis ───────────────────────────────────
    if multi and len(tab_objs) > 1:
        with tab_objs[1]:
            st.subheader("安全交集与冲突")
            safe = multi.get("safe_intersection", [])
            coeff = multi.get("conflict_coefficient", 0)
            c1, c2 = st.columns(2)
            c1.metric("安全交集大小", len(safe))
            c2.metric("冲突系数", f"{coeff:.2f}")

            cm = multi.get("conflict_matrix", [])
            if cm:
                st.subheader("冲突热力图")
                labels = sorted({k for e in cm for k in e.get("effects", {})})
                obs_ids = [e["obs_id"] for e in cm]
                z_data = []
                for e in cm:
                    row = []
                    for lab in labels:
                        row.append(e.get("effects", {}).get(lab, 0))
                    z_data.append(row)

                fig_heat = go.Figure(data=go.Heatmap(z=z_data, x=labels, y=obs_ids, colorscale="RdBu", zmid=0, text=[[f"{v:.3f}" for v in row] for row in z_data], texttemplate="%{text}"))
                fig_heat.update_layout(xaxis_title="模型", yaxis_title="观测值 ID", height=400)
                st.plotly_chart(fig_heat, use_container_width=True)

                st.subheader("冲突详情")
                st.dataframe(pd.DataFrame(cm), use_container_width=True, hide_index=True)

            # Pareto overlay: all models t-value vs n_deleted
            st.subheader("帕累托曲线")
            fig_pareto = go.Figure()
            for mname, mres in models.items():
                sc = mres.get("spec_curves", [])
                for curve in sc:
                    path = curve.get("path", [])
                    n_del = [p["n_del"] for p in path]
                    t_vals = [abs(p["t"]) for p in path]
                    fig_pareto.add_trace(go.Scatter(x=n_del, y=t_vals, mode="lines+markers", name=mname))
            fig_pareto.add_hline(y=1.96, line_dash="dash", line_color="gray")
            fig_pareto.update_layout(xaxis_title="删除数量", yaxis_title="|t 值|", height=400)
            st.plotly_chart(fig_pareto, use_container_width=True)

            # Status matrix
            st.subheader("模型达标状态")
            sbm = multi.get("status_by_model", {})
            if sbm:
                st.dataframe(pd.DataFrame(sbm).T, use_container_width=True)

            # Export with drop_all_safe
            if safe:
                df_all = st.session_state.df.copy()
                df_all["drop_all_safe"] = 0
                for oid in safe:
                    if oid < len(df_all):
                        df_all.iloc[oid, df_all.columns.get_loc("drop_all_safe")] = 1
                st.download_button("下载 CSV (drop_all_safe)", export_multi_csv(st.session_state.df, safe), "sigadjust_multi.csv", "text/csv")

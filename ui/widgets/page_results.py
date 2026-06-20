"""page_results.py — Results display with Plotly charts, export, and multi-model views.

SingleModelResults: per-model t-value curves, F-curves, deletion path, export.
MultiModelResults: conflict heatmap, Pareto overlay, status matrix.
ResultsPage: QTabWidget combining both views.
"""

import json
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.offline as py_offline
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QFileDialog, QInputDialog, QGroupBox, QFrame, QHeaderView,
    QMessageBox, QApplication,
)
from PySide6.QtWebEngineWidgets import QWebEngineView


# ═════════════════════════════════════════════════════════════════════
#  Chart builders
# ═════════════════════════════════════════════════════════════════════

def _build_t_value_chart(model_result):
    """Build |t|-value vs deletion count Plotly figure."""
    fig = go.Figure()
    for curve in model_result.get("spec_curves", []):
        path = curve.get("path", [])
        if path:
            x = [p["n_del"] for p in path]
            y = [abs(p["t"]) for p in path]
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines+markers",
                name=curve.get("control_set", "default"),
            ))
    fig.add_hline(
        y=1.96, line_dash="dash", line_color="red",
        annotation_text="p=0.05",
    )
    fig.update_layout(
        title="|t| 值随删除步数变化",
        xaxis_title="删除步数",
        yaxis_title="|t| 统计量",
        template="plotly_white",
        height=350,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def _build_f_chart(model_result):
    """Build F-statistic curve for 2SLS models."""
    f_curve = model_result.get("f_curve", [])
    if not f_curve:
        return None
    fig = go.Figure()
    x = [p["n_del"] for p in f_curve]
    y = [p["f_stat"] for p in f_curve]
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name="F-stat"))
    fig.add_hline(
        y=10, line_dash="dash", line_color="red",
        annotation_text="F=10",
    )
    fig.update_layout(
        title="F 统计量随删除步数变化",
        xaxis_title="删除步数",
        yaxis_title="F 统计量",
        template="plotly_white",
        height=300,
        margin=dict(l=50, r=20, t=40, b=40),
    )
    return fig


def _build_conflict_heatmap(multi_result):
    """Build conflict heatmap from multi_model data."""
    cm = multi_result.get("conflict_matrix", [])
    if not cm:
        return None
    obs_ids = [str(row["obs_id"]) for row in cm]
    model_names = list(cm[0].get("effects", {}).keys())
    z = [[row["effects"].get(m, 0) for m in model_names] for row in cm]
    fig = go.Figure(data=go.Heatmap(
        z=z, x=model_names, y=obs_ids,
        colorscale="RdBu", zmid=0,
        hovertemplate="Obs %{y}<br>%{x}: %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title="冲突热力图",
        xaxis_title="模型",
        yaxis_title="观测序号",
        template="plotly_white",
        height=400,
        margin=dict(l=50, r=20, t=50, b=80),
    )
    return fig


def _build_pareto_chart(models_results):
    """Overlay all models" t-value curves on one chart."""
    fig = go.Figure()
    for name, result in models_results.items():
        curves = result.get("spec_curves", [])
        if curves and curves[0].get("path"):
            path = curves[0]["path"]
            fig.add_trace(go.Scatter(
                x=[p["n_del"] for p in path],
                y=[abs(p["t"]) for p in path],
                mode="lines+markers",
                name=name,
            ))
    fig.add_hline(
        y=1.96, line_dash="dash", line_color="red",
        annotation_text="p=0.05",
    )
    fig.update_layout(
        title="帕累托叠加: |t| 随删除步数",
        xaxis_title="删除步数",
        yaxis_title="|t| 统计量",
        template="plotly_white",
        height=350,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def _fig_to_html(fig):
    """Convert a Plotly figure to a full HTML string."""
    plot_div = py_offline.plot(fig, include_plotlyjs="cdn", output_type="div")
    return (
        "<html><body style='margin:0;padding:0;background:white;'>"
        + plot_div
        + "</body></html>"
    )


# ═════════════════════════════════════════════════════════════════════
#  SingleModelResults
# ═════════════════════════════════════════════════════════════════════

class SingleModelResults(QWidget):
    """Single model results tab: charts, table, and export."""

    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Model selector
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("模型:"))
        self._model_combo = QComboBox()
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        sel_layout.addWidget(self._model_combo)
        sel_layout.addStretch()
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.clicked.connect(self.refresh)
        sel_layout.addWidget(self._refresh_btn)
        layout.addLayout(sel_layout)

        # Metric cards
        card_layout = QHBoxLayout()
        card_layout.setSpacing(8)
        self._metric_labels = {}
        for label in ("基准 |t|", "最终 |t|", "基准 p", "最终 p", "R²", "已删除"):
            card = QFrame()
            card.setFixedHeight(60)
            card.setMinimumWidth(100)
            card.setStyleSheet(
                "QFrame{background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 4, 8, 4)
            cl.addWidget(QLabel(label, styleSheet="color:#9ca3af;font-size:10px;"))
            val = QLabel("--", styleSheet="color:#111827;font-size:15px;font-weight:bold;")
            cl.addWidget(val)
            self._metric_labels[label] = val
            card_layout.addWidget(card)
        layout.addLayout(card_layout)

        # Charts
        self._t_chart_view = QWebEngineView()
        self._t_chart_view.setMinimumHeight(300)
        layout.addWidget(self._t_chart_view, stretch=3)

        self._f_chart_view = QWebEngineView()
        self._f_chart_view.setMinimumHeight(250)
        self._f_chart_view.setVisible(False)
        layout.addWidget(self._f_chart_view, stretch=2)

        # Deletion path table
        self._path_table = QTableWidget()
        self._path_table.setStyleSheet(
            "QTableWidget{border:1px solid #e5e7eb;font-size:12px;}"
            "QHeaderView::section{background:#f9fafb;border:1px solid #e5e7eb;padding:4px 6px;font-weight:bold;}"
        )
        self._path_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._path_table.setAlternatingRowColors(True)
        self._path_table.horizontalHeader().setStretchLastSection(False)
        self._path_table.verticalHeader().setDefaultSectionSize(22)
        layout.addWidget(self._path_table, stretch=2)

        # Export section
        export_group = QGroupBox("导出")
        export_layout = QVBoxLayout(export_group)

        btn_layout = QHBoxLayout()
        self._export_csv_btn = QPushButton("CSV")
        self._export_dta_btn = QPushButton("DTA")
        self._export_excel_btn = QPushButton("Excel")
        self._export_html_btn = QPushButton("HTML")
        for b in (self._export_csv_btn, self._export_dta_btn,
                  self._export_excel_btn, self._export_html_btn):
            b.setStyleSheet(
                "QPushButton{border:1px solid #d1d5db;border-radius:4px;"
                "padding:4px 12px;font-size:12px;}"
                "QPushButton:hover{background:#f3f4f6;}"
            )
            btn_layout.addWidget(b)
        btn_layout.addStretch()
        export_layout.addLayout(btn_layout)

        # Light DTA + merge command
        lt_layout = QHBoxLayout()
        self._light_dta_btn = QPushButton("轻量 DTA (ID 变量)")
        self._light_dta_btn.setStyleSheet(
            "QPushButton{border:1px solid #d1d5db;border-radius:4px;"
            "padding:4px 12px;font-size:12px;}"
            "QPushButton:hover{background:#f3f4f6;}"
        )
        lt_layout.addWidget(self._light_dta_btn)
        self._merge_cmd_label = QLabel("")
        self._merge_cmd_label.setStyleSheet(
            "color:#374151;font-size:11px;font-family:Consolas;padding:4px;"
            "border:1px solid #e5e7eb;border-radius:4px;background:#f9fafb;"
        )
        self._merge_cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lt_layout.addWidget(self._merge_cmd_label, stretch=1)
        export_layout.addLayout(lt_layout)

        layout.addWidget(export_group)

        # Connect export buttons
        self._export_csv_btn.clicked.connect(lambda: self._export("csv"))
        self._export_dta_btn.clicked.connect(lambda: self._export("dta"))
        self._export_excel_btn.clicked.connect(lambda: self._export("excel"))
        self._export_html_btn.clicked.connect(lambda: self._export("html"))
        self._light_dta_btn.clicked.connect(self._export_light)

    def refresh(self):
        """Reload results from ViewModel and update display."""
        results = self._vm.results
        if not results:
            return
        models = results.get("models", {})
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for name in models:
            self._model_combo.addItem(name, name)
        if self._model_combo.count() > 0:
            self._model_combo.setCurrentIndex(0)
        self._model_combo.blockSignals(False)
        self._on_model_changed(0)

    def _on_model_changed(self, idx):
        """Update display for the selected model."""
        results = self._vm.results
        if not results:
            return
        name = self._model_combo.currentData()
        if not name:
            return
        model_result = results.get("models", {}).get(name, {})
        self._show_model_result(name, model_result)

    def _show_model_result(self, name, model_result):
        """Render charts, table, and metrics for one model."""
        baseline = model_result.get("baseline") or {}
        final = model_result.get("final") or {}
        from math import sqrt

        # Metrics
        bt = abs(baseline.get("t_stat", 0))
        ft = abs(final.get("t_stat", 0)) if final else bt
        bp = baseline.get("p_value", 0)
        fp = final.get("p_value", 0) if final else bp
        r2 = final.get("r_squared", baseline.get("r_squared", 0))
        nd = final.get("n_deleted", 0) if final else 0

        self._metric_labels["基准 |t|"].setText(f"{bt:.3f}")
        self._metric_labels["最终 |t|"].setText(f"{ft:.3f}" if final else "--")
        self._metric_labels["基准 p"].setText(f"{bp:.4f}")
        self._metric_labels["最终 p"].setText(f"{fp:.4f}" if final else "--")
        self._metric_labels["R²"].setText(f"{r2:.4f}")
        self._metric_labels["已删除"].setText(str(nd))

        # t-value chart
        t_fig = _build_t_value_chart(model_result)
        self._t_chart_view.setHtml(_fig_to_html(t_fig))

        # F chart (2SLS only)
        f_fig = _build_f_chart(model_result)
        if f_fig:
            self._f_chart_view.setHtml(_fig_to_html(f_fig))
            self._f_chart_view.setVisible(True)
        else:
            self._f_chart_view.setVisible(False)

        # Deletion path table
        path = model_result.get("deletion_path", [])
        if path:
            cols = list(path[0].keys())
            self._path_table.setColumnCount(len(cols))
            self._path_table.setHorizontalHeaderLabels(cols)
            self._path_table.setRowCount(len(path))
            for r, row in enumerate(path):
                for c, col in enumerate(cols):
                    val = row.get(col, "")
                    if col == "obs_id" and isinstance(val, (int, float)):
                        val = int(val) + 1
                    item = QTableWidgetItem(str(val) if val is not None else "")
                    self._path_table.setItem(r, c, item)
            self._path_table.horizontalHeader().setStretchLastSection(False)
            column_widths = {"step": 40, "obs_id": 60, "t_after": 100, "p_after": 100, "direction": 90}
            for c_idx, col in enumerate(cols):
                width = column_widths.get(col, 100)
                self._path_table.setColumnWidth(c_idx, width)
        else:
            self._path_table.setRowCount(0)
            self._path_table.setColumnCount(0)

    def _export(self, fmt: str):
        """Export the current model in the selected format."""
        results = self._vm.results
        if not results:
            return
        name = self._model_combo.currentData()
        if not name:
            return
        model_result = results.get("models", {}).get(name, {})
        final = model_result.get("final") or {}
        deleted_obs = final.get("deleted_obs", [])
        df = self._vm.df
        if df is None:
            return

        baseline = model_result.get("baseline")
        deletion_path = model_result.get("deletion_path", [])

        ext_map = {"csv": ".csv", "dta": ".dta", "excel": ".xlsx", "html": ".html"}
        ext = ext_map.get(fmt, ".csv")
        fpath, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt.upper()}", f"sigadjust_{name}{ext}",
            f"{fmt.upper()} Files (*{ext})",
        )
        if not fpath:
            return

        from core.export import (
            export_full_csv, export_full_dta,
            export_full_excel, export_full_html,
        )
        try:
            if fmt == "csv":
                data = export_full_csv(df, deleted_obs, name)
            elif fmt == "dta":
                data = export_full_dta(df, deleted_obs, name)
            elif fmt == "excel":
                data = export_full_excel(df, deleted_obs, name, baseline, deletion_path)
            elif fmt == "html":
                t_fig = _build_t_value_chart(model_result)
                f_fig = _build_f_chart(model_result)
                figures = [t_fig]
                if f_fig:
                    figures.append(f_fig)
                multi = results.get("multi_model")
                cm = multi.get("conflict_matrix") if multi else None
                data = export_full_html(
                    df, deleted_obs, name, figures,
                    baseline, deletion_path, cm,
                )
            with open(fpath, "wb") as f:
                f.write(data)
        except Exception as e:
            QMessageBox.warning(self, "导出错误", str(e))

    def _export_light(self):
        """Export lightweight DTA with id vars selection."""
        results = self._vm.results
        if not results:
            return
        name = self._model_combo.currentData()
        if not name:
            return
        final = results["models"][name].get("final") or {}
        deleted_obs = final.get("deleted_obs", [])
        df = self._vm.df
        if df is None:
            return

        id_vars_str, ok = QInputDialog.getText(
            self, "轻量 DTA 导出",
            "输入 ID 变量名，空格分隔:",
            text="id",
        )
        if not ok or not id_vars_str:
            return
        id_vars = id_vars_str.strip().split()

        fpath, _ = QFileDialog.getSaveFileName(
            self, "Export Light DTA", f"drop_{name}.dta",
            "DTA Files (*.dta)",
        )
        if not fpath:
            return

        from core.export import export_light_dta
        try:
            merge_cmd = export_light_dta(df, deleted_obs, name, id_vars, fpath)
            self._merge_cmd_label.setText(merge_cmd)
        except Exception as e:
            QMessageBox.warning(self, "导出错误", str(e))


# ═════════════════════════════════════════════════════════════════════
#  MultiModelResults
# ═════════════════════════════════════════════════════════════════════

class MultiModelResults(QWidget):
    """Multi-model conflict analysis tab."""

    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Metric cards
        card_layout = QHBoxLayout()
        card_layout.setSpacing(8)
        self._mm_labels = {}
        for label in ("冲突系数", "安全交集", "分析模型数"):
            card = QFrame()
            card.setFixedHeight(60)
            card.setMinimumWidth(120)
            card.setStyleSheet(
                "QFrame{background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 4, 8, 4)
            cl.addWidget(QLabel(label, styleSheet="color:#9ca3af;font-size:10px;"))
            val = QLabel("--", styleSheet="color:#111827;font-size:15px;font-weight:bold;")
            cl.addWidget(val)
            self._mm_labels[label] = val
            card_layout.addWidget(card)
        card_layout.addStretch()
        layout.addLayout(card_layout)

        # Conflict heatmap
        self._heatmap_view = QWebEngineView()
        self._heatmap_view.setMinimumHeight(300)
        layout.addWidget(self._heatmap_view, stretch=3)

        # Pareto overlay
        self._pareto_view = QWebEngineView()
        self._pareto_view.setMinimumHeight(300)
        layout.addWidget(self._pareto_view, stretch=3)

        # Status table
        self._status_table = QTableWidget()
        self._status_table.setStyleSheet(
            "QTableWidget{border:1px solid #e5e7eb;font-size:12px;}"
            "QHeaderView::section{background:#f9fafb;border:1px solid #e5e7eb;padding:4px 6px;font-weight:bold;}"
        )
        self._status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._status_table.setAlternatingRowColors(True)
        self._status_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._status_table, stretch=2)

        # Multi export
        export_layout = QHBoxLayout()
        self._mm_export_btn = QPushButton("导出多模型 CSV")
        self._mm_export_btn.setStyleSheet(
            "QPushButton{border:1px solid #d1d5db;border-radius:4px;"
            "padding:4px 12px;font-size:12px;}"
            "QPushButton:hover{background:#f3f4f6;}"
        )
        self._mm_export_btn.clicked.connect(self._export_multi)
        export_layout.addWidget(self._mm_export_btn)
        export_layout.addStretch()
        layout.addLayout(export_layout)

    def refresh(self):
        """Reload multi-model data and update display."""
        results = self._vm.results
        if not results or not results.get("multi_model"):
            return
        multi = results["multi_model"]
        models = results.get("models", {})

        cc = multi.get("conflict_coefficient", 0)
        si = len(multi.get("safe_intersection", []))
        nm = len(models)

        self._mm_labels["冲突系数"].setText(f"{cc:.3f}")
        self._mm_labels["安全交集"].setText(str(si))
        self._mm_labels["分析模型数"].setText(str(nm))

        # Heatmap
        hm = _build_conflict_heatmap(multi)
        if hm:
            self._heatmap_view.setHtml(_fig_to_html(hm))
        else:
            self._heatmap_view.setHtml("<html><body><p>No conflict data.</p></body></html>")

        # Pareto
        pa = _build_pareto_chart(models)
        self._pareto_view.setHtml(_fig_to_html(pa))

        # Status table
        status_by = multi.get("status_by_model", {})
        if status_by:
            cols = ["模型", "目标方向", "最终方向", "状态"]
            self._status_table.setColumnCount(len(cols))
            self._status_table.setHorizontalHeaderLabels(cols)
            self._status_table.setRowCount(len(status_by))
            for r, (mname, st) in enumerate(status_by.items()):
                self._status_table.setItem(r, 0, QTableWidgetItem(mname))
                self._status_table.setItem(r, 1, QTableWidgetItem(st.get("target", "")))
                self._status_table.setItem(r, 2, QTableWidgetItem(st.get("achieved", "")))
                self._status_table.setItem(r, 3, QTableWidgetItem(st.get("status", "")))
            self._status_table.resizeColumnsToContents()
        else:
            self._status_table.setRowCount(0)
            self._status_table.setColumnCount(0)

    def _export_multi(self):
        """Export multi-model CSV."""
        results = self._vm.results
        if not results or not results.get("multi_model"):
            return
        multi = results["multi_model"]
        df = self._vm.df
        if df is None:
            return

        fpath, _ = QFileDialog.getSaveFileName(
            self, "导出多模型 CSV", "sigadjust_multi.csv",
            "CSV Files (*.csv)",
        )
        if not fpath:
            return

        from core.export import export_multi_csv_full
        si = multi.get("safe_intersection", [])
        model_names = list(results.get("models", {}).keys())
        data = export_multi_csv_full(df, si, model_names)
        with open(fpath, "wb") as f:
            f.write(data)


# ═════════════════════════════════════════════════════════════════════
#  ResultsPage
# ═════════════════════════════════════════════════════════════════════

class ResultsPage(QWidget):
    """Tab 4: Results display with single-model and multi-model views."""

    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tab_widget = QTabWidget()
        self._single_results = SingleModelResults(self._vm)
        self._multi_results = MultiModelResults(self._vm)
        self._tab_widget.addTab(self._single_results, "单模型结果")
        self._tab_widget.addTab(self._multi_results, "多模型联动")
        layout.addWidget(self._tab_widget)

    def _connect_signals(self):
        self._vm.calculation_finished.connect(self._on_results_ready)

    def _on_results_ready(self, results: dict):
        """Refresh both sub-tabs when new results arrive."""
        self._single_results.refresh()
        if results.get("multi_model"):
            self._multi_results.refresh()
            self._tab_widget.setCurrentIndex(1)
        else:
            self._tab_widget.setCurrentIndex(0)

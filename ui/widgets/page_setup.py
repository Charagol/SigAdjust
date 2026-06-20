"""page_setup.py — Model configuration page for SigAdjust V2.

Provides the SetupPage (Tab 2) with multi-model form, variable conflict
coordination, and configuration persistence. Coordinates all VariableSelector
instances and manages the XY mutual exclusivity and Control filtering rules.

Architecture:
  SetupPage owns all conflict coordination logic.
  ModelCard is a passive form container; all variable selectors are exposed
  as public attributes so SetupPage can connect to their signals directly.
"""

import json
import os
import pandas as pd
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QComboBox, QDoubleSpinBox, QCheckBox,
    QSlider, QScrollArea, QFileDialog, QMessageBox,
    QDialog, QTextEdit, QFrame, QSizePolicy, QFormLayout,
)
from ui.widgets.variable_selector import VariableSelector
from ui.widgets.stata_parser import StataCommandParser


# ═════════════════════════════════════════════════════════════════════
#  StataImportDialog (placeholder for Phase 11)
# ═════════════════════════════════════════════════════════════════════

class StataImportDialog(QDialog):
    """Dialog for Stata command import: parse, validate, preview, fill form."""

    def __init__(self, viewmodel, setup_page, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._setup_page = setup_page
        self._parsed = None
        self.setWindowTitle("Stata 命令导入")
        self.resize(620, 520)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        info = QLabel(
            "\u7c98\u8d34 Stata \u56de\u5f52\u547d\u4ee4\u3002\u652f\u6301:\n"
            "  reg/regress, logit, probit, ologit, oprobit, reghdfe\n"
            "  \u652f\u6301: i.var \u56e0\u5b50\u53d8\u91cf, absorb(), robust\n"
            "  \u4e0d\u652f\u6301: ##, $macro, if/in/weight, cluster"
        )
        info.setStyleSheet("color: #6b7280; font-size: 12px; padding: 4px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        self._input = QTextEdit()
        self._input.setPlaceholderText("示例: reg Y X c1 c2 i.industry, robust")
        self._input.setMaximumHeight(80)
        layout.addWidget(self._input)
        btn_row = QHBoxLayout()
        self._parse_btn = QPushButton("解析")
        self._parse_btn.setStyleSheet(
            "QPushButton { background: #4f46e5; color: white; border: none;"
            " border-radius: 4px; padding: 6px 16px; }"
            " QPushButton:hover { background: #4338ca; }"
        )
        btn_row.addWidget(self._parse_btn)
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self._msg_label = QLabel("")
        self._msg_label.setWordWrap(True)
        self._msg_label.setVisible(False)
        layout.addWidget(self._msg_label)
        self._preview = QGroupBox("解析结果")
        self._preview.setVisible(False)
        preview_layout = QVBoxLayout(self._preview)
        self._preview_text = QLabel("")
        self._preview_text.setWordWrap(True)
        self._preview_text.setStyleSheet("font-size: 13px; padding: 4px;")
        preview_layout.addWidget(self._preview_text)
        self._confirm_btn = QPushButton("确认导入")
        self._confirm_btn.setStyleSheet(
            "QPushButton { background: #059669; color: white; border: none;"
            " border-radius: 4px; padding: 8px 20px; font-size: 13px; }"
            " QPushButton:hover { background: #047857; }"
        )
        preview_layout.addWidget(self._confirm_btn)
        layout.addWidget(self._preview)

    def _connect_signals(self):
        self._parse_btn.clicked.connect(self._on_parse)
        self._confirm_btn.clicked.connect(self._on_confirm)

    def _on_parse(self):
        text = self._input.toPlainText().strip()
        if not text:
            self._show_error("请输入命令。")
            return
        result = StataCommandParser.parse(text)
        self._parsed = result
        if not result["success"]:
            self._show_error(result["error"] or "Parse failed.")
            return
        df = self._vm.df
        all_controls = list(result["control_vars"])
        expanded_cols = []
        if result["factor_vars"] and df is not None:
            for fv in result["factor_vars"]:
                if fv not in df.columns:
                    self._show_error("因子变量 [" + fv + "] 在数据中未找到。")
                    return
                try:
                    dummies = pd.get_dummies(df[fv], prefix="_C", drop_first=True)
                    for col in dummies.columns:
                        if col not in df.columns:
                            df[col] = dummies[col]
                        expanded_cols.append(col)
                    all_controls.extend(expanded_cols)
                except Exception as e:
                    self._show_error("因子变量展开失败 [" + fv + "]: " + str(e))
                    return
        result["control_vars"] = all_controls
        result["_expanded_cols"] = expanded_cols
        col_set = set(df.columns) if df is not None else set()
        val_errors = []
        if result["dependent_var"] and result["dependent_var"] not in col_set:
            val_errors.append("Y 变量 [" + result["dependent_var"] + "] 不在数据集中")
        if result["key_var"] and result["key_var"] not in col_set:
            val_errors.append("X 变量 [" + result["key_var"] + "] 不在数据集中")
        for ctrl in result["control_vars"]:
            if ctrl not in col_set:
                val_errors.append("控制变量 [" + ctrl + "] 不在数据集中")
        for fv in result["factor_vars"]:
            if fv not in col_set:
                val_errors.append("因子变量 [" + fv + "] not in dataset")
        if val_errors:
            self._show_error("\n".join(val_errors))
            return
        self._show_preview(result)

    def _show_error(self, msg):
        self._msg_label.setStyleSheet("color: #dc2626; font-size: 12px; padding: 4px;")
        self._msg_label.setText(msg)
        self._msg_label.setVisible(True)
        self._preview.setVisible(False)

    def _show_preview(self, result):
        self._msg_label.setVisible(False)
        lines = [
            "  模型类型: " + result["model_type"].upper(),
            "  被解释变量 (Y): " + result["dependent_var"],
            "  核心解释变量 (X): " + result["key_var"],
        ]
        if result["control_vars"]:
            lines.append("  控制变量: " + ", ".join(result["control_vars"]))
        if result["factor_vars"]:
            lines.append("  因子变量 (已展开): " + ", ".join(result["factor_vars"]))
        if result["fe_vars"]:
            lines.append("  固定效应: " + ", ".join(result["fe_vars"]))
        if result["se_type"] == "robust":
            lines.append("  标准误: 稳健")
        if result.get("warning"):
            lines.append("\n  Warning: " + result["warning"])
        self._preview_text.setText("\n".join(lines))
        self._preview.setVisible(True)

    def _on_confirm(self):
        if not self._parsed or not self._parsed["success"]:
            return
        p = self._parsed
        sp = self._setup_page
        while len(sp._model_cards) > 1:
            sp._on_remove_model(len(sp._model_cards) - 1)
        card = sp._model_cards[0]
        card.y_selector.set_selected([])
        card.x_selector.set_selected([])
        card.control_selector.set_selected([])
        type_map = {"ols": 0, "logit": 1, "probit": 2, "fe": 3}
        idx = type_map.get(p["model_type"], 0)
        card._type_combo.setCurrentIndex(idx)
        if p["dependent_var"]:
            card.y_selector.set_selected([p["dependent_var"]])
        if p["key_var"]:
            card.x_selector.set_selected([p["key_var"]])
        if p["control_vars"]:
            card.control_selector.set_selected(p["control_vars"])
        if p["model_type"] == "fe" and p["fe_vars"]:
            card.fe_selector.set_selected(p["fe_vars"])
        sp._update_all_control_items()
        if p.get("_expanded_cols"):
            from core.validation import get_missing_summary
            sp._vm._columns_info = get_missing_summary(sp._vm.df)
        card._name_input.setText("Stata_" + p["model_type"])
        self.accept()

#  ModelCard
# ═════════════════════════════════════════════════════════════════════

MODEL_TYPES = ["ols", "logit", "probit", "fe", "iv"]
DIRECTION_OPTIONS = ["正向显著", "负向显著"] # "positive", "negative" UI labels


class ModelCard(QGroupBox):
    """A single model configuration card inside SetupPage.

    Exposes public attributes for all variable selectors so the parent
    SetupPage can connect signals and coordinate conflicts directly.
    """

    removed = Signal(int)

    def __init__(self, model_index: int, all_vars: list[str], parent=None):
        super().__init__(parent)
        self._index = model_index
        self._all_vars = all_vars
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Title bar: name + type + delete button ──
        title_layout = QHBoxLayout()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText(f"Model {self._index + 1}")
        self._name_input.setStyleSheet("font-weight: bold; font-size: 13px;")
        title_layout.addWidget(QLabel("名称:"))
        title_layout.addWidget(self._name_input)

        title_layout.addWidget(QLabel("类型:"))
        self._type_combo = QComboBox()
        self._type_combo.setMinimumWidth(100)
        self._type_combo.addItems([t.upper() for t in MODEL_TYPES])
        self._type_combo.setCurrentIndex(0)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        title_layout.addWidget(self._type_combo)

        title_layout.addStretch()

        self._delete_btn = QPushButton("\u00d7 Delete")
        self._delete_btn.setStyleSheet("""
            QPushButton {
                color: #dc2626;
                border: 1px solid #fca5a5;
                border-radius: 4px;
                padding: 2px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
            }
        """)
        self._delete_btn.clicked.connect(lambda: self.removed.emit(self._index))
        title_layout.addWidget(self._delete_btn)

        layout.addLayout(title_layout)

        # ── Variable selectors ──
        # Y (dependent variable)
        self.y_selector = VariableSelector()
        self.y_selector.set_items(self._all_vars)
        self.y_selector.set_max_selection(1)
        layout.addWidget(QLabel("被解释变量 (Y):"))
        layout.addWidget(self.y_selector)

        # X (key explanatory variable)
        self.x_selector = VariableSelector()
        self.x_selector.set_items(self._all_vars)
        self.x_selector.set_max_selection(2)
        layout.addWidget(QLabel("核心解释变量 (X):"))
        layout.addWidget(self.x_selector)

        # Control variables
        self.control_selector = VariableSelector()
        self.control_selector.set_items(self._all_vars)
        layout.addWidget(QLabel("控制变量:"))
        layout.addWidget(self.control_selector)

        # ── Conditional fields ──
        # FE vars (hidden by default, shown when type=FE)
        self._fe_group = QWidget()
        fe_layout = QVBoxLayout(self._fe_group)
        fe_layout.setContentsMargins(0, 0, 0, 0)
        self.fe_selector = VariableSelector()
        self.fe_selector.set_items(self._all_vars)
        fe_layout.addWidget(QLabel("固定效应变量:"))
        fe_layout.addWidget(self.fe_selector)
        self._fe_group.setVisible(False)
        layout.addWidget(self._fe_group)

        # IV fields (hidden by default, shown when type=2SLS)
        self._iv_group = QWidget()
        iv_layout = QVBoxLayout(self._iv_group)
        iv_layout.setContentsMargins(0, 0, 0, 0)
        self.endog_selector = VariableSelector()
        self.endog_selector.set_items(self._all_vars)
        iv_layout.addWidget(QLabel("内生变量:"))
        iv_layout.addWidget(self.endog_selector)
        self.instr_selector = VariableSelector()
        self.instr_selector.set_items(self._all_vars)
        iv_layout.addWidget(QLabel("工具变量:"))
        iv_layout.addWidget(self.instr_selector)
        self._iv_group.setVisible(False)
        layout.addWidget(self._iv_group)

        # ── Priority + target p ──
        params_layout = QHBoxLayout()

        params_layout.addWidget(QLabel("优先级:"))
        self._priority_slider = QSlider(Qt.Horizontal)
        self._priority_slider.setRange(1, 5)
        self._priority_slider.setValue(5)
        self._priority_slider.setTickPosition(QSlider.TicksBelow)
        self._priority_slider.setTickInterval(1)
        self._priority_slider.setFixedWidth(120)
        params_layout.addWidget(self._priority_slider)
        self._priority_label = QLabel("5")
        self._priority_label.setFixedWidth(20)
        self._priority_slider.valueChanged.connect(
            lambda v: self._priority_label.setText(str(v))
        )
        params_layout.addWidget(self._priority_label)

        params_layout.addSpacing(20)
        params_layout.addWidget(QLabel("目标 p:"))
        self._target_p_spin = QDoubleSpinBox()
        self._target_p_spin.setRange(0.001, 0.50)
        self._target_p_spin.setSingleStep(0.005)
        self._target_p_spin.setDecimals(3)
        self._target_p_spin.setValue(0.05)
        self._target_p_spin.setFixedWidth(80)
        params_layout.addWidget(self._target_p_spin)
        params_layout.addStretch()

        layout.addLayout(params_layout)

    def _on_type_changed(self, text: str):
        """Show/hide conditional fields based on model type."""
        model_type = text.lower()
        self._fe_group.setVisible(model_type == "fe")
        self._iv_group.setVisible(model_type == "iv")
        # Clear irrelevant fields when switching types
        if model_type != "fe":
            self.fe_selector.set_selected([])
            self.fe_selector.set_items(self._all_vars)
        if model_type != "iv":
            self.endog_selector.set_selected([])
            self.endog_selector.set_items(self._all_vars)
            self.instr_selector.set_selected([])
            self.instr_selector.set_items(self._all_vars)

    def get_config(self) -> dict:
        """Return this model's configuration dict (compute_input model entry)."""
        config = {
            "name": self._name_input.text() or f"Model {self._index + 1}",
            "type": self._type_combo.currentText().lower(),
            "dependent_var": self._get_single_selection(self.y_selector),
            "key_var": self._get_single_selection(self.x_selector),
            "control_vars": self.control_selector.get_selected(),
            "priority": self._priority_slider.value(),
            "target_p": self._target_p_spin.value(),
            "direction": "both",
        }
        model_type = config["type"]
        if model_type == "fe":
            config["fe_vars"] = self.fe_selector.get_selected()
        elif model_type == "iv":
            config["endogenous_var"] = self._get_single_selection(
                self.endog_selector
            )
            config["instruments"] = self.instr_selector.get_selected()
        return config

    def set_config(self, config: dict):
        """Populate form fields from a configuration dict."""
        self._name_input.setText(config.get("name", ""))
        model_type = config.get("type", "ols")
        # Find index in MODEL_TYPES
        type_upper = model_type.upper()
        idx = 0
        for i, t in enumerate(MODEL_TYPES):
            if t == model_type or t.upper() == type_upper:
                idx = i
                break
        self._type_combo.setCurrentIndex(idx)

        dv = config.get("dependent_var", "")
        if dv:
            self.y_selector.set_selected([dv])
        kv = config.get("key_var", "")
        if kv:
            self.x_selector.set_selected([kv])

        self.control_selector.set_selected(config.get("control_vars", []))
        self._priority_slider.setValue(config.get("priority", 5))
        self._target_p_spin.setValue(config.get("target_p", 0.05))

        if model_type == "fe":
            self.fe_selector.set_selected(config.get("fe_vars", []))
        elif model_type == "iv":
            endog = config.get("endogenous_var", "")
            if endog:
                self.endog_selector.set_selected([endog])
            self.instr_selector.set_selected(config.get("instruments", []))

    def set_control_items(self, items: list[str]):
        """Update the candidate list for the Control VariableSelector."""
        self.control_selector.set_items(items)

    def set_fe_items(self, items: list[str]):
        """Update the candidate list for the FE VariableSelector."""
        self.fe_selector.set_items(items)

    def set_endog_items(self, items: list[str]):
        """Update the candidate list for the Endogenous VariableSelector."""
        self.endog_selector.set_items(items)

    def set_instr_items(self, items: list[str]):
        """Update the candidate list for the Instruments VariableSelector."""
        self.instr_selector.set_items(items)

    def update_all_items(self, items: list[str]):
        """Refresh all VariableSelector candidate lists."""
        self._all_vars = items
        self.y_selector.set_items(items)
        self.x_selector.set_items(items)
        self.control_selector.set_items(items)
        self.fe_selector.set_items(items)
        self.endog_selector.set_items(items)
        self.instr_selector.set_items(items)

    def set_delete_visible(self, visible: bool):
        """Show or hide the delete button."""
        self._delete_btn.setVisible(visible)

    def set_name_focus(self):
        """Focus on the name input."""
        self._name_input.setFocus()
        self._name_input.selectAll()

    @property
    def model_index(self) -> int:
        return self._index

    @staticmethod
    def _get_single_selection(selector: VariableSelector) -> str:
        """Get the first (only) value from a single-selection selector."""
        selected = selector.get_selected()
        return selected[0] if selected else ""


# ═════════════════════════════════════════════════════════════════════
#  SetupPage
# ═════════════════════════════════════════════════════════════════════

class SetupPage(QWidget):
    """Tab 2: Multi-model configuration page.

    Manages global settings, a variable number of model cards, variable
    conflict coordination, Stata import placeholder, config persistence,
    and the Start Analysis workflow.
    """

    request_start_analysis = Signal()

    def __init__(self, viewmodel, main_window, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._main_window = main_window
        self._model_cards: list[ModelCard] = []
        self._updating_selectors = False
        self._test_mode = False
        self._last_error = chr(34) + chr(34)
        self._setup_ui()
        self._connect_signals()
        self._add_model_card()

    # ── UI Setup ─────────────────────────────────────────────────────

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # ── Global settings ──
        global_group = QGroupBox("全局设置")
        global_layout = QHBoxLayout(global_group)
        global_layout.setSpacing(16)

        global_layout.addWidget(QLabel("显著性阈值:"))
        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.001, 0.50)
        self._threshold_spin.setSingleStep(0.005)
        self._threshold_spin.setDecimals(3)
        self._threshold_spin.setValue(0.05)
        self._threshold_spin.setFixedWidth(80)
        global_layout.addWidget(self._threshold_spin)

        global_layout.addWidget(QLabel("最大删除比:"))
        self._max_pct_spin = QDoubleSpinBox()
        self._max_pct_spin.setRange(0.1, 50.0)
        self._max_pct_spin.setSingleStep(0.5)
        self._max_pct_spin.setDecimals(1)
        self._max_pct_spin.setValue(5.0)
        self._max_pct_spin.setSuffix("%")
        self._max_pct_spin.setFixedWidth(80)
        global_layout.addWidget(self._max_pct_spin)

        self._direction_checkbox = QCheckBox("启用方向控制")
        self._direction_combo = QComboBox()
        self._direction_combo.addItems(DIRECTION_OPTIONS)
        self._direction_combo.setMinimumWidth(100)
        self._direction_combo.setVisible(False)
        self._direction_checkbox.toggled.connect(self._direction_combo.setVisible)
        self._direction_checkbox.setChecked(False)
        global_layout.addWidget(self._direction_checkbox)
        global_layout.addWidget(self._direction_combo)

        global_layout.addStretch()

        # Stata import button (placeholder)
        self._stata_btn = QPushButton("Stata 导入")
        self._stata_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
                color: #374151;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
            }
        """)
        global_layout.addWidget(self._stata_btn)

        main_layout.addWidget(global_group)

        # ── Model cards scroll area ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()
        scroll.setWidget(self._cards_container)
        main_layout.addWidget(scroll, stretch=1)

        # ── Add model button ──
        self._add_btn = QPushButton("+ 添加模型")
        self._add_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                border: 2px dashed #d1d5db;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                color: #6b7280;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                color: #374151;
            }
        """)
        main_layout.addWidget(self._add_btn)

        # ── Bottom action bar ──
        bottom_bar = QHBoxLayout()
        self._save_btn = QPushButton("保存配置")
        self._load_btn = QPushButton("加载配置")
        self._start_btn = QPushButton("开始分析")
        self._start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        bottom_bar.addWidget(self._save_btn)
        bottom_bar.addWidget(self._load_btn)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self._start_btn)
        main_layout.addLayout(bottom_bar)

    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self._add_btn.clicked.connect(self._add_model_card)
        self._stata_btn.clicked.connect(self._on_stata_import)
        self._save_btn.clicked.connect(self._on_save_config)
        self._load_btn.clicked.connect(self._on_load_config)
        self._start_btn.clicked.connect(self._on_start_analysis)
        self._vm.data_loaded.connect(self._on_data_loaded)

    # ── Model Card Management ────────────────────────────────────────

    def _get_all_vars(self) -> list[str]:
        """Get the list of all available variable names from loaded data."""
        info = self._vm.columns_info
        if not info:
            return []
        return list(info.get("columns", {}).keys())

    def _add_model_card(self):
        """Add a new model card (max 4)."""
        if len(self._model_cards) >= 4:
            return
        idx = len(self._model_cards)
        card = ModelCard(idx, self._get_all_vars())
        card.removed.connect(self._on_remove_model)
        card.y_selector.selection_changed.connect(
            lambda sel, i=idx: self._on_y_changed(i, sel)
        )
        card.x_selector.selection_changed.connect(
            lambda sel, i=idx: self._on_x_changed(i, sel)
        )
        card.set_delete_visible(idx > 0)
        # Insert before the stretch
        self._cards_layout.insertWidget(
            self._cards_layout.count() - 1, card
        )
        self._model_cards.append(card)
        self._update_add_button()
        # Update control items for all cards
        self._update_all_control_items()

    def _on_remove_model(self, index: int):
        """Remove a model card by its index."""
        if len(self._model_cards) <= 1:
            return
        card = self._model_cards[index]
        self._cards_layout.removeWidget(card)
        card.deleteLater()
        self._model_cards.pop(index)
        # Re-index remaining cards
        for i, c in enumerate(self._model_cards):
            c._index = i
            c.removed.disconnect()
            c.removed.connect(lambda idx, ci=i: self._on_remove_model(ci))
            c.set_delete_visible(i > 0)
            # Reconnect signals with new index
            c.y_selector.selection_changed.disconnect()
            c.x_selector.selection_changed.disconnect()
            c.y_selector.selection_changed.connect(
                lambda sel, ci=i: self._on_y_changed(ci, sel)
            )
            c.x_selector.selection_changed.connect(
                lambda sel, ci=i: self._on_x_changed(ci, sel)
            )
        self._update_add_button()
        self._update_all_control_items()

    def _update_add_button(self):
        """Show/hide the Add Model button based on current count."""
        self._add_btn.setVisible(len(self._model_cards) < 4)

    # ── Variable Conflict Coordination ───────────────────────────────

    def _get_all_selected_x(self) -> set[str]:
        """Get the union of all X selections across all models."""
        result = set()
        for card in self._model_cards:
            result.update(card.x_selector.get_selected())
        return result

    def _get_all_selected_y(self) -> set[str]:
        """Get the union of all Y selections across all models."""
        result = set()
        for card in self._model_cards:
            result.update(card.y_selector.get_selected())
        return result

    def _get_selected_control(self, card: ModelCard) -> set[str]:
        """Get Control selections for a specific card."""
        return set(card.control_selector.get_selected())

    def _on_x_changed(self, model_idx: int, selected: list[str]):
        """Handle X selection change: XY mutual exclusion + Control updates."""
        if self._updating_selectors:
            return
        self._updating_selectors = True

        # XY mutual exclusion: remove from Y in the same model
        card = self._model_cards[model_idx]
        y_selected = card.y_selector.get_selected()
        for var in selected:
            if var in y_selected:
                y_selected.remove(var)
                card.y_selector.set_selected(y_selected)
                break  # Y is single-select, only one possible conflict

        # Update Control items for all models
        self._update_all_control_items()

        self._updating_selectors = False
        self._test_mode = False
        self._last_error = chr(34) + chr(34)

    def _on_y_changed(self, model_idx: int, selected: list[str]):
        """Handle Y selection change: XY mutual exclusion + Control updates."""
        if self._updating_selectors:
            return
        self._updating_selectors = True

        # XY mutual exclusion: remove from X in the same model
        card = self._model_cards[model_idx]
        x_selected = card.x_selector.get_selected()
        for var in selected:
            if var in x_selected:
                x_selected.remove(var)
                card.x_selector.set_selected(x_selected)
                break  # X is single-select

        # Update Control items for all models
        self._update_all_control_items()

        self._updating_selectors = False
        self._test_mode = False
        self._last_error = chr(34) + chr(34)

    def _update_all_control_items(self):
        """Update Control VariableSelector items:
        Control candidates = all_vars - X_union - Y_union
        """
        all_vars = self._get_all_vars()
        x_union = self._get_all_selected_x()
        y_union = self._get_all_selected_y()
        excluded = x_union | y_union
        control_items = [v for v in all_vars if v not in excluded]

        for card in self._model_cards:
            card.control_selector.set_items(control_items)
            # Update conditional selectors too
            card.fe_selector.set_items(control_items)
            card.endog_selector.set_items(control_items)
            card.instr_selector.set_items(control_items)

    # ── Action Handlers ──────────────────────────────────────────────

    def _on_data_loaded(self, df):
        """Refresh all variable selectors when new data is loaded."""
        all_vars = self._get_all_vars()
        for card in self._model_cards:
            card.update_all_items(all_vars)
        self._update_all_control_items()

    def _on_stata_import(self):
        """Open the Stata import placeholder dialog."""
        dialog = StataImportDialog(self._vm, self)
        dialog.exec()

    def _on_save_config(self):
        """Save current configuration to a JSON file."""
        config = self._build_config()
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存配置", "sigadjust_config.json",
            "JSON Files (*.json)",
        )
        if not filepath:
            return
        try:
            self._vm.save_config(filepath)
        except ValueError:
            # If no config exists yet, write the built config
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

    def _on_load_config(self):
        """Load and apply configuration from a JSON file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "加载配置", "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            QMessageBox.warning(self, "Error", "配置文件加载失败。")
            return

        # Validate version
        version = config.get("version", "")
        if version not in ("1.0", "2.0"):
            QMessageBox.warning(
                self, "不兼容",
                "不支持的配置版本: " + version + "，需要 1.0 或 2.0。",
            )
            return

        # Apply global settings
        gs = config.get("global_settings", {})
        self._threshold_spin.setValue(gs.get("significance_threshold", 0.05))
        self._max_pct_spin.setValue(gs.get("max_deletions_pct", 5.0))
        direction = gs.get("direction", "both")
        if direction == "both":
            self._direction_checkbox.setChecked(False)
        else:
            self._direction_checkbox.setChecked(True)
            if direction == "positive":
                self._direction_combo.setCurrentText(DIRECTION_OPTIONS[0])
            else:
                self._direction_combo.setCurrentText(DIRECTION_OPTIONS[1])

        # Rebuild model cards
        models_config = config.get("models", [])
        # Remove existing cards (except first if we need at least 1)
        while self._model_cards:
            card = self._model_cards.pop(0)
            self._cards_layout.removeWidget(card)
            card.deleteLater()

        # Add cards from config
        all_vars = self._get_all_vars()
        for mc in models_config:
            idx = len(self._model_cards)
            card = ModelCard(idx, all_vars)
            card.removed.connect(
                lambda i=None, ci=idx: self._on_remove_model(ci)
            )
            card.y_selector.selection_changed.connect(
                lambda sel, ci=idx: self._on_y_changed(ci, sel)
            )
            card.x_selector.selection_changed.connect(
                lambda sel, ci=idx: self._on_x_changed(ci, sel)
            )
            card.set_config(mc)
            card.set_delete_visible(idx > 0)
            self._cards_layout.insertWidget(
                self._cards_layout.count() - 1, card
            )
            self._model_cards.append(card)

        self._update_add_button()
        # Fire callbacks manually for the first card to sync selectors
        self._update_all_control_items()

    def _on_start_analysis(self):
        """Validate, build config, write to ViewModel, emit signal, switch tab."""
        # Validate
        errors = []
        for i, card in enumerate(self._model_cards):
            model_name = card._name_input.text() or f"Model {i+1}"
            if not card.y_selector.get_selected():
                errors.append(f"{model_name}: Please select a dependent variable (Y).")
            if not card.x_selector.get_selected():
                errors.append(f"{model_name}: Please select a key variable (X).")
            model_type = card._type_combo.currentText().lower()
            if model_type == "iv":
                if not card.endog_selector.get_selected():
                    errors.append(
                        f"{model_name}: Please select an endogenous variable."
                    )
                if not card.instr_selector.get_selected():
                    errors.append(
                        f"{model_name}: Please select at least one instrument."
                    )

        if errors:
            msg = "\n\n".join(errors)
            self._last_error = msg
            if not self._test_mode:
                QMessageBox.warning(self, "验证错误", msg)
            return

        # Build config and write to ViewModel
        config = self._build_config()
        self._vm.config = config
        # The setter already emits config_changed

        # Switch to Tab 3 (Computation / index 2)
        self._vm.run_calculation()
        self._main_window.switch_to_tab(2)

    def set_test_mode(self, enabled: bool):
        self._test_mode = enabled

    def _build_config(self) -> dict:
        """Build the full compute_input dict from current form state."""
        models = [card.get_config() for card in self._model_cards]
        if self._direction_checkbox.isChecked():
            direction = "positive" if self._direction_combo.currentText() == DIRECTION_OPTIONS[0] else "negative"
        else:
            direction = "both"
        config = {
            "version": "2.0",
            "global_settings": {
                "significance_threshold": self._threshold_spin.value(),
                "max_deletions_pct": self._max_pct_spin.value(),
                "direction": direction,
            },
            "models": models,
        }
        return config

"""page_progress.py — Computation progress page + background worker.

ComputationWorker runs the pipeline in a QThread and emits progress signals.
ComputationProgressPage displays the progress bar and status updates.
"""

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QProgressBar, QLabel, QPushButton,
    QHBoxLayout, QFrame,
)


# ═════════════════════════════════════════════════════════════════════
#  ComputationWorker
# ═════════════════════════════════════════════════════════════════════

class ComputationWorker(QObject):
    """Runs the computation pipeline in a background thread.

    Emits progress and result signals that the UI can connect to.
    """

    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(int, int, str)  # current, total, message

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config

    def run(self):
        """Execute the pipeline. Call this from QThread.started."""
        try:
            df = self._config["df"]
            settings = self._config.get("global_settings", {})
            models_config = self._config.get("models", [])
            total = len(models_config)
            results = {}
            max_pct = settings.get("max_deletions_pct", 5.0)

            for i, model_cfg in enumerate(models_config):
                name = model_cfg["name"]
                model_type = model_cfg.get("type", "ols")
                target_p = model_cfg.get(
                    "target_p", settings.get("significance_threshold", 0.05)
                )
                self.progress.emit(
                    i, total,
                    f"Model {i+1}/{total}: {name} ({model_type})..."
                )

                dv = model_cfg["dependent_var"]
                kv = model_cfg["key_var"]
                cv = model_cfg.get("control_vars", [])

                if model_type == "ols":
                    from core.greedy_search import greedy_deletion
                    result = greedy_deletion(
                        df=df, dependent_var=dv, key_var=kv,
                        control_vars=cv,
                        significance_threshold=target_p,
                        max_deletions_pct=max_pct,
                    )
                elif model_type in ("logit", "probit"):
                    from core.models.logit_model import run_logit_greedy
                    result = run_logit_greedy(
                        df=df, dependent_var=dv, key_var=kv,
                        control_vars=cv,
                        significance_threshold=target_p,
                        max_deletions_pct=max_pct,
                        model_type=model_type,
                    )
                elif model_type == "iv":
                    from core.models.iv_model import run_iv_greedy
                    result = run_iv_greedy(
                        df=df, dependent_var=dv, key_var=kv,
                        control_vars=cv,
                        endogenous_var=model_cfg.get("endogenous_var", kv),
                        instruments=model_cfg.get("instruments", []),
                        significance_threshold=target_p,
                        max_deletions_pct=max_pct,
                    )
                elif model_type == "fe":
                    from core.models.fe_model import run_fe_greedy
                    result = run_fe_greedy(
                        df=df, dependent_var=dv, key_var=kv,
                        control_vars=cv,
                        fe_vars=model_cfg.get("fe_vars", []),
                        significance_threshold=target_p,
                        max_deletions_pct=max_pct,
                    )
                else:
                    result = {
                        "baseline": None, "deletion_path": [],
                        "final": None, "spec_curves": [],
                    }
                results[name] = result

            multi = None
            if len(models_config) > 1:
                self.progress.emit(total, total, "多模型仲裁中...")
                from core.multi_model import arbitrate
                multi = arbitrate(results, models_config, df)

            self.progress.emit(total, total, "完成!")
            self.finished.emit({"models": results, "multi_model": multi})

        except Exception as e:
            self.error.emit(str(e))


# ═════════════════════════════════════════════════════════════════════
#  ComputationProgressPage
# ═════════════════════════════════════════════════════════════════════

class ComputationProgressPage(QWidget):
    """Tab 3: Shows computation progress and status."""

    def __init__(self, viewmodel, main_window, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self._main_window = main_window
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        self._title_label = QLabel("分析进行中...")
        self._title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #374151;"
        )
        self._title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedWidth(400)
        self._progress_bar.setFixedHeight(24)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                text-align: center;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #4f46e5;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self._progress_bar, 0, Qt.AlignCenter)

        self._status_label = QLabel("初始化中...")
        self._status_label.setStyleSheet("color: #6b7280; font-size: 13px;")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _connect_signals(self):
        self._vm.progress_updated.connect(self._on_progress)
        self._vm.calculation_finished.connect(self._on_finished)
        self._vm.calculation_error.connect(self._on_error)

    def _on_progress(self, current: int, total: int, message: str):
        """Update progress bar and status text."""
        if total > 0:
            pct = int(current * 100 / total)
            self._progress_bar.setValue(pct)
        self._status_label.setText(message)

        if total > 0 and current >= total:
            self._title_label.setText("完成!")
            self._title_label.setStyleSheet(
                "font-size: 18px; font-weight: bold; color: #059669;"
            )

    def _on_finished(self, results: dict):
        """Pipeline completed normally."""
        self._title_label.setText("分析完成")
        self._title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #059669;"
        )
        self._status_label.setText("所有模型处理完成。")
        self._main_window.switch_to_tab(3)

    def _on_error(self, msg: str):
        """Pipeline encountered an error."""
        self._title_label.setText("错误")
        self._title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #dc2626;"
        )
        self._status_label.setText(f"Error: {msg}")

    def reset(self):
        """Reset progress display for a new computation."""
        self._progress_bar.setValue(0)
        self._title_label.setText("分析进行中...")
        self._title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #374151;"
        )
        self._status_label.setText("初始化中...")

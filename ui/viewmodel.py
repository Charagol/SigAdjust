"""SigAdjust ViewModel — single source of truth for all application state.

This ViewModel acts as a bridge between core/ computation and UI widgets.
It holds all shared state as QObject properties and uses Qt Signal/Slot
for reactive updates. Widgets never hold data directly; they subscribe
to ViewModel signals and access its properties.
"""

import json
import os
import pandas as pd
from PySide6.QtCore import QObject, Signal


class SigAdjustViewModel(QObject):
    """Single ViewModel instance holding all application state.

    Signals:
        data_loaded: Emitted after successful data import, carries the DataFrame.
        progress_updated: Emitted during computation (current, total, message).
        calculation_finished: Emitted when pipeline completes, carries compute_output dict.
        calculation_error: Emitted on failure, carries error message string.
    """

    data_loaded = Signal(pd.DataFrame)
    progress_updated = Signal(int, int, str)   # current, total, message
    calculation_finished = Signal(dict)
    config_changed = Signal(dict)
    calculation_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df: pd.DataFrame | None = None
        self._columns_info: dict = {}
        self._config: dict | None = None
        self._results: dict | None = None
        self._filepath: str | None = None

    # ── Properties ───────────────────────────────────────────────────

    @property
    def df(self) -> pd.DataFrame | None:
        """Raw uploaded/imported DataFrame."""
        return self._df

    @property
    def columns_info(self) -> dict:
        """Column metadata dict compatible with V1 format.

        Shape: { "n_rows": N, "n_cols": K, "columns": { col: {...} } }
        Produced by core.validation.get_missing_summary().
        """
        return self._columns_info

    @property
    def config(self) -> dict | None:
        """Model configuration dict conforming to compute_input contract."""
        return self._config

    @config.setter
    def config(self, value: dict | None):
        self._config = value
        if value is not None:
            self.config_changed.emit(value)

    @property
    def results(self) -> dict | None:
        """Computation results dict conforming to compute_output contract."""
        return self._results

    @results.setter
    def results(self, value: dict | None):
        self._results = value

    @property
    def filepath(self) -> str | None:
        """Path to the currently loaded data file."""
        return self._filepath

    # ── Public Methods ───────────────────────────────────────────────

    def load_data(self, filepath: str) -> bool:
        """Load a data file into the ViewModel.

        Supports CSV, Stata DTA, and Excel (.xlsx / .xls) formats.
        On success, updates df and columns_info properties and emits
        data_loaded.

        Args:
            filepath: Absolute or relative path to the data file.

        Returns:
            True if loading succeeded, False otherwise.
        """
        if not os.path.isfile(filepath):
            return False

        ext = os.path.splitext(filepath)[1].lower()

        try:
            if ext == ".csv":
                df = pd.read_csv(filepath)
            elif ext == ".dta":
                df = pd.read_stata(filepath)
            elif ext in (".xlsx", ".xls"):
                df = pd.read_excel(filepath)
            else:
                return False

            if df.empty:
                return False

            # Compute column metadata using core validation utility
            from core.validation import get_missing_summary
            columns_info = get_missing_summary(df)

            self._df = df
            self._columns_info = columns_info
            self._filepath = filepath

            self.data_loaded.emit(df)
            return True

        except Exception:
            return False

    def run_calculation(self) -> None:
        """Run the full computation pipeline (placeholder).

        Will be implemented in Phase 12 with QThread-based execution.
        """
        pass

    def save_config(self, path: str) -> None:
        """Save current config to a JSON file."""
        if self._config is None:
            raise ValueError("No config to save")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def load_config(self, path: str) -> bool:
        """Load config from a JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self._config = config
            self.config_changed.emit(config)
            return True
        except Exception:
            return False


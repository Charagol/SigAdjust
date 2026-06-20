"""Tests for SigAdjustViewModel — state management and signal emission.

Requires QApplication to be initialized before QObject-based tests.
"""

import os
import sys

import pandas as pd
import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication


# ── QApplication fixture (session-scoped, created once) ──────────────

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication once for all tests in the session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# ── Module imports (after QApplication is set up) ────────────────────

@pytest.fixture(scope="module")
def viewmodel(qapp):
    """Create a ViewModel instance for testing."""
    from ui.viewmodel import SigAdjustViewModel
    return SigAdjustViewModel()


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures")


# ── Tests ─────────────────────────────────────────────────────────────

class TestViewModelInit:
    """ViewModel initialization state tests."""

    def test_init_state_none(self, viewmodel):
        """All properties should be None/empty on initialization."""
        assert viewmodel.df is None
        assert viewmodel.columns_info == {}
        assert viewmodel.config is None
        assert viewmodel.results is None
        assert viewmodel.filepath is None

    def test_init_type(self, viewmodel):
        """ViewModel should be a QObject."""
        from PySide6.QtCore import QObject
        assert isinstance(viewmodel, QObject)


class TestViewModelLoadData:
    """ViewModel.load_data functionality tests."""

    def test_load_data_csv(self, viewmodel):
        """Loading a valid CSV should populate df and columns_info."""
        csv_path = os.path.join(DATA_DIR, "sample.csv")
        assert os.path.isfile(csv_path), f"Sample CSV not found: {csv_path}"

        result = viewmodel.load_data(csv_path)
        assert result is True

        # df should be set
        assert viewmodel.df is not None
        assert isinstance(viewmodel.df, pd.DataFrame)
        assert len(viewmodel.df) == 12
        assert "y" in viewmodel.df.columns

        # columns_info should be populated
        info = viewmodel.columns_info
        assert info["n_rows"] == 12
        assert info["n_cols"] == 5
        assert "y" in info["columns"]
        assert info["columns"]["y"]["dtype"] == "float64"

    def test_load_data_not_found(self, viewmodel):
        """Loading a nonexistent file should return False."""
        result = viewmodel.load_data("/nonexistent/file.csv")
        assert result is False

    def test_load_data_signal_emitted(self, qapp):
        """The data_loaded signal should fire after successful load."""
        from ui.viewmodel import SigAdjustViewModel
        vm = SigAdjustViewModel()

        signal_fired = [False]
        received_df = [None]

        def on_data_loaded(df):
            signal_fired[0] = True
            received_df[0] = df

        vm.data_loaded.connect(on_data_loaded)

        csv_path = os.path.join(DATA_DIR, "sample.csv")
        result = vm.load_data(csv_path)
        assert result is True

        # Process pending Qt events to deliver the signal
        # (In a real app, the event loop handles this. For the test,
        #  we can call processEvents.)
        qapp.processEvents()

        assert signal_fired[0] is True, "data_loaded signal was not emitted"
        assert received_df[0] is not None

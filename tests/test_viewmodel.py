"""Tests for SigAdjustViewModel — state management and signal emission.

Uses qtbot (pytest-qt) for QApplication lifecycle management.
"""

import os

import pandas as pd
import pytest

from ui.viewmodel import SigAdjustViewModel


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures")


class TestViewModelInit:
    """ViewModel initialization state tests."""

    def test_init_state_none(self, qtbot):
        """All properties should be None/empty on initialization."""
        vm = SigAdjustViewModel()
        assert vm.df is None
        assert vm.columns_info == {}
        assert vm.config is None
        assert vm.results is None
        assert vm.filepath is None

    def test_init_type(self, qtbot):
        """ViewModel should be a QObject."""
        from PySide6.QtCore import QObject
        vm = SigAdjustViewModel()
        assert isinstance(vm, QObject)


class TestViewModelLoadData:
    """ViewModel.load_data functionality tests."""

    def test_load_data_csv(self, qtbot):
        """Loading a valid CSV should populate df and columns_info."""
        vm = SigAdjustViewModel()
        csv_path = os.path.join(DATA_DIR, "sample.csv")
        assert os.path.isfile(csv_path)

        result = vm.load_data(csv_path)
        assert result is True

        assert vm.df is not None
        assert isinstance(vm.df, pd.DataFrame)
        assert len(vm.df) == 12
        assert "y" in vm.df.columns

        info = vm.columns_info
        assert info["n_rows"] == 12
        assert info["n_cols"] == 5
        assert "y" in info["columns"]
        assert info["columns"]["y"]["dtype"] == "float64"

    def test_load_data_not_found(self, qtbot):
        """Loading a nonexistent file should return False."""
        vm = SigAdjustViewModel()
        result = vm.load_data("/nonexistent/file.csv")
        assert result is False

    def test_load_data_signal_emitted(self, qtbot):
        """The data_loaded signal should fire after successful load."""
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

        qtbot.waitUntil(lambda: signal_fired[0], timeout=2000)
        assert received_df[0] is not None

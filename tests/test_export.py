"""Tests for core.export — order column, light DTA, merge command.

Pure logic tests, no Qt dependency.
"""

import os
import sys
import tempfile
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.export import (
    export_full_csv,
    export_full_dta,
    _build_drop_df,
    export_light_dta,
)


@pytest.fixture
def sample_df():
    """Small DataFrame for export testing."""
    return pd.DataFrame({
        "id": [101, 102, 103, 104, 105],
        "year": [2020, 2020, 2021, 2021, 2022],
        "y": [1.0, 2.0, 3.0, 4.0, 5.0],
        "x": [0.1, 0.2, 0.3, 0.4, 0.5],
    })


class TestExportOrderColumn:
    """Verify drop_{name}_order column existence and values."""

    def test_build_drop_df_has_order_column(self, sample_df):
        """_build_drop_df should include drop_{name}_order."""
        deleted = [0, 2, 4]
        out = _build_drop_df(sample_df, deleted, "main")
        assert "drop_main_order" in out.columns
        assert list(out["drop_main_order"]) == [1, 0, 2, 0, 3]

    def test_build_drop_df_drop_flag(self, sample_df):
        """drop_{name} should be 1 for deleted obs, 0 otherwise."""
        deleted = [1, 3]
        out = _build_drop_df(sample_df, deleted, "test_model")
        expected = [0, 1, 0, 1, 0]
        assert list(out["drop_test_model"]) == expected

    def test_export_full_csv_contains_order(self, sample_df):
        """export_full_csv should include order column."""
        deleted = [0, 4]
        data = export_full_csv(sample_df, deleted, "ols_model")
        csv_text = data.decode("utf-8")
        assert "drop_ols_model_order" in csv_text
        assert "drop_ols_model" in csv_text


class TestExportLightDta:
    """Verify light DTA export behavior."""

    def test_light_dta_only_id_vars_and_drop(self, sample_df):
        """Light DTA should only contain id vars + drop columns."""
        deleted = [0, 2]
        with tempfile.NamedTemporaryFile(suffix=".dta", delete=False) as f:
            tmp_path = f.name
        try:
            merge_cmd = export_light_dta(
                sample_df, deleted, "model1",
                ["id", "year"], tmp_path,
            )
            loaded = pd.read_stata(tmp_path)
            cols = set(loaded.columns)
            expected = {"id", "year", "drop_model1", "drop_model1_order"}
            # Should NOT contain y or x
            assert "y" not in cols
            assert "x" not in cols
            # Should contain all expected
            for col in expected:
                assert col in cols, f"Missing column: {col}"
        finally:
            os.unlink(tmp_path)

    def test_light_dta_merge_command_format(self, sample_df):
        """Merge command should have proper Stata syntax."""
        deleted = [0]
        with tempfile.NamedTemporaryFile(suffix=".dta", delete=False) as f:
            tmp_path = f.name
        try:
            merge_cmd = export_light_dta(
                sample_df, deleted, "main",
                ["id", "year"], tmp_path,
            )
            assert "merge 1:1" in merge_cmd
            assert "keepusing(" in merge_cmd
            assert "nogen" in merge_cmd
        finally:
            os.unlink(tmp_path)

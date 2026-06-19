"""Tests for core.validation — pure functions, no Streamlit dependency."""

import numpy as np
import pandas as pd
import pytest
from core.validation import (
    check_column_exists,
    check_column_type,
    validate_columns,
    get_missing_summary,
)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_df():
    """Small DataFrame with numeric, string, and missing values."""
    return pd.DataFrame({
        "x": [1.0, 2.0, 3.0, np.nan, 5.0],
        "y": [0.1, 0.2, 0.3, 0.4, 0.5],
        "group": ["A", "B", "A", "B", "A"],
    })


# ── check_column_exists ───────────────────────────────────────────────

def test_check_column_exists_hit(sample_df):
    ok, msg = check_column_exists(sample_df, "x")
    assert ok is True
    assert msg == "OK"


def test_check_column_exists_miss(sample_df):
    ok, msg = check_column_exists(sample_df, "z")
    assert ok is False
    assert "不在数据中" in msg


# ── check_column_type ─────────────────────────────────────────────────

def test_check_column_type_numeric(sample_df):
    ok, msg = check_column_type(sample_df, "x", "numeric")
    assert ok is True


def test_check_column_type_numeric_fail(sample_df):
    ok, msg = check_column_type(sample_df, "group", "numeric")
    assert ok is False
    assert "应为数值类型" in msg


def test_check_column_type_string(sample_df):
    ok, msg = check_column_type(sample_df, "group", "string")
    assert ok is True


def test_check_column_type_missing_col(sample_df):
    ok, msg = check_column_type(sample_df, "z", "numeric")
    assert ok is False
    assert "不在数据中" in msg


# ── validate_columns ──────────────────────────────────────────────────

def test_validate_columns_all_exist(sample_df):
    status_map, errors = validate_columns(sample_df, ["x", "y", "group"])
    assert status_map == {"x": True, "y": True, "group": True}
    assert errors == []


def test_validate_columns_partial_miss(sample_df):
    status_map, errors = validate_columns(sample_df, ["x", "z", "w"])
    assert status_map == {"x": True, "z": False, "w": False}
    assert len(errors) == 2


# ── get_missing_summary ───────────────────────────────────────────────

def test_get_missing_summary(sample_df):
    result = get_missing_summary(sample_df)
    assert result["n_rows"] == 5
    assert result["n_cols"] == 3
    cols = result["columns"]
    assert cols["x"]["n_missing"] == 1
    assert cols["y"]["n_missing"] == 0
    assert cols["x"]["missing_rate"] == 0.2
    assert cols["y"]["missing_rate"] == 0.0


def test_get_missing_summary_empty_df():
    df = pd.DataFrame()
    result = get_missing_summary(df)
    assert result["n_rows"] == 0
    assert result["n_cols"] == 0
    assert result["columns"] == {}

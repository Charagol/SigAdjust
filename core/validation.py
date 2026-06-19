"""Input validation utilities — pure functions, no Streamlit dependency.

All functions accept and return standard Python types (dict, list, DataFrame),
making them independently testable and reusable across any UI framework.
"""

import pandas as pd
import numpy as np


def check_column_exists(df: pd.DataFrame, col_name: str) -> tuple[bool, str]:
    """Check whether a column name exists in the DataFrame."""
    if col_name in df.columns:
        return True, "OK"
    return False, f"列 '{col_name}' 不在数据中。可用列: {list(df.columns)}"


def check_column_type(
    df: pd.DataFrame,
    col_name: str,
    expected_dtype: str = "numeric",
) -> tuple[bool, str]:
    """Check whether a column has the expected data type."""
    if col_name not in df.columns:
        return False, f"列 '{col_name}' 不在数据中。"
    col = df[col_name]
    if expected_dtype == "numeric":
        if pd.api.types.is_numeric_dtype(col):
            return True, "OK"
        return False, f"列 '{col_name}' 应为数值类型，实际类型: {col.dtype}"
    if expected_dtype == "string":
        if pd.api.types.is_string_dtype(col) or pd.api.types.is_categorical_dtype(col):
            return True, "OK"
        return False, f"列 '{col_name}' 应为字符串/分类类型，实际类型: {col.dtype}"
    return False, f"未知的预期类型: {expected_dtype}"


def validate_columns(
    df: pd.DataFrame,
    required_cols: list[str],
) -> tuple[dict[str, bool], list[str]]:
    """Batch validate that all required columns exist in the DataFrame."""
    status_map = {}
    errors = []
    for col in required_cols:
        ok, msg = check_column_exists(df, col)
        status_map[col] = ok
        if not ok:
            errors.append(msg)
    return status_map, errors


def get_missing_summary(df: pd.DataFrame) -> dict:
    """Compute per-column missing-value statistics."""
    n_rows, n_cols = df.shape
    columns_info = {}
    for col in df.columns:
        n_total = len(df)
        n_missing = int(df[col].isna().sum())
        missing_rate = n_missing / n_total if n_total > 0 else 0.0
        columns_info[col] = {
            "dtype": str(df[col].dtype),
            "missing_rate": round(missing_rate, 4),
            "n_missing": n_missing,
            "n_total": n_total,
        }
    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "columns": columns_info,
    }

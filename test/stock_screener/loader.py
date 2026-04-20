"""Data loading module — CSV reader with validation and cleaning."""

import pandas as pd
from pathlib import Path


def load_csv(file_path: str) -> pd.DataFrame:
    """Load stock data from a CSV file.

    - Strips whitespace from column names
    - Converts numeric-looking columns to float (non-parseable → NaN)
    - Preserves 'code' and 'name' as strings

    Args:
        file_path: Path to the CSV file.

    Returns:
        Cleaned DataFrame.

    Raises:
        FileNotFoundError: File does not exist.
        ValueError: File is empty or unreadable.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {file_path}")
    if path.stat().st_size == 0:
        raise ValueError(f"数据文件为空: {file_path}")

    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise ValueError(f"无法读取 CSV 文件: {e}")

    if df.empty:
        raise ValueError(f"数据文件没有有效数据行: {file_path}")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Auto-detect and convert numeric columns (skip code/name)
    text_cols = {"code", "name"}
    for col in df.columns:
        if col.lower() in text_cols:
            df[col] = df[col].astype(str).str.strip()
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    """Return column names that contain numeric data."""
    return [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]


def get_all_columns(df: pd.DataFrame) -> list[str]:
    """Return all column names."""
    return list(df.columns)

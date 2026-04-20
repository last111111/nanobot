"""Output formatter — table and JSON output for humans and agents."""

import json
import math

import pandas as pd

try:
    from .field_metadata import get_field_label
except ImportError:
    from field_metadata import get_field_label


def format_table(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    """Format DataFrame as an aligned text table.

    Args:
        df: Data to format.
        columns: Optional subset of columns to include.

    Returns:
        Formatted string, or an empty-result message.
    """
    if columns:
        cols = [c for c in columns if c in df.columns]
        if cols:
            df = df[cols]

    if df.empty:
        return "筛选结果为空，没有符合条件的股票。"

    display_df = df.rename(columns={col: get_field_label(col) for col in df.columns})
    return display_df.to_string(index=False)


def format_json(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    """Format DataFrame as a JSON array.

    NaN values are converted to null for clean JSON output.

    Args:
        df: Data to format.
        columns: Optional subset of columns to include.

    Returns:
        JSON string.
    """
    if columns:
        cols = [c for c in columns if c in df.columns]
        if cols:
            df = df[cols]

    records = df.to_dict(orient="records")

    # Replace NaN/inf with None for valid JSON
    for record in records:
        for k, v in record.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                record[k] = None

    return json.dumps(records, ensure_ascii=False, indent=2)


def format_error(message: str, output_format: str = "table") -> str:
    """Format an error message in the appropriate output style.

    In JSON mode, returns a JSON object with an 'error' key.
    In table mode, returns a prefixed text string.
    """
    if output_format == "json":
        return json.dumps({"error": message}, ensure_ascii=False, indent=2)
    return f"错误: {message}"

"""Output formatter - table and JSON output for humans and agents."""

import json
import math

import pandas as pd

try:
    from .field_metadata import get_field_label
except ImportError:
    from field_metadata import get_field_label


def format_table(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    """Format DataFrame as an aligned text table."""
    if columns:
        cols = [col for col in columns if col in df.columns]
        if cols:
            df = df[cols]

    if df.empty:
        return "筛选结果为空，没有符合条件的股票。"

    display_df = df.rename(columns={col: get_field_label(col) for col in df.columns})
    return display_df.to_string(index=False)


def format_json(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    """Format DataFrame as a stable JSON array."""
    if columns:
        cols = [col for col in columns if col in df.columns]
        if cols:
            df = df[cols]

    records = df.to_dict(orient="records")
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                record[key] = None

    return json.dumps(records, ensure_ascii=False, indent=2)


def format_error(message: str, output_format: str = "table") -> str:
    """Format an error message using the requested output format."""
    if output_format == "json":
        return json.dumps({"error": message}, ensure_ascii=False, indent=2)
    return f"错误: {message}"

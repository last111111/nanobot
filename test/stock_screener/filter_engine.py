"""Filter engine — parse filter expressions and apply them to DataFrames."""

import operator
import re
from dataclasses import dataclass

import pandas as pd

try:
    from .field_metadata import format_fields_for_display, resolve_field_name
except ImportError:
    from field_metadata import format_fields_for_display, resolve_field_name

# Supported comparison operators (order matters: >= before >)
OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
}

OPERATOR_DESCRIPTIONS = {
    ">": "大于",
    ">=": "大于等于",
    "<": "小于",
    "<=": "小于等于",
    "==": "等于",
}

FILTER_PATTERN = re.compile(r"^([^\s]+)\s*(>=|<=|==|>|<)\s*([^\s]+)$")


@dataclass
class Filter:
    """A single filter condition: field op value."""
    field: str
    op: str
    value: float | str
    value_is_field: bool = False

    def __str__(self) -> str:
        return f"{self.field} {self.op} {self.value}"


def parse_filter(expr: str) -> Filter:
    """Parse a string like 'pe < 20' into a Filter.

    Raises:
        ValueError: If the expression cannot be parsed.
    """
    if not isinstance(expr, str):
        raise ValueError(f"筛选条件必须是字符串，收到: {type(expr).__name__}")

    expr = expr.strip()
    m = FILTER_PATTERN.match(expr)
    if not m:
        raise ValueError(
            f"无法解析筛选条件: '{expr}'\n"
            f"正确格式: 'field op value'，例如 'pe < 20'\n"
            f"支持的运算符: >, >=, <, <=, =="
        )

    raw_value = m.group(3)
    try:
        value: float | str = float(raw_value)
        value_is_field = False
    except ValueError:
        value = raw_value
        value_is_field = True

    return Filter(
        field=m.group(1),
        op=m.group(2),
        value=value,
        value_is_field=value_is_field,
    )


def apply_filters(
    df: pd.DataFrame,
    filters: list[Filter],
) -> tuple[pd.DataFrame, list[str]]:
    """Apply a list of filters to a DataFrame.

    Filters are applied in sequence (AND logic).
    Rows with NaN in the filtered column are excluded.

    Returns:
        (filtered_df, error_messages)
    """
    errors: list[str] = []
    result = df

    for f in filters:
        left_field = resolve_field_name(f.field, result.columns)
        if left_field is None:
            available = format_fields_for_display(result.columns)
            errors.append(
                f"筛选字段 '{f.field}' 不存在。可用字段: {available}"
            )
            continue

        op_func = OPERATORS.get(f.op)
        if op_func is None:
            errors.append(
                f"不支持的运算符: '{f.op}'。支持: >, >=, <, <=, =="
            )
            continue

        left_col = result[left_field]
        if not pd.api.types.is_numeric_dtype(left_col):
            numeric_fields = format_fields_for_display(
                [c for c in result.columns if pd.api.types.is_numeric_dtype(result[c])]
            )
            errors.append(
                f"筛选字段 '{f.field}' 不是数值字段。可筛选字段: {numeric_fields}"
            )
            continue

        if f.value_is_field:
            right_field = resolve_field_name(str(f.value), result.columns)
            if right_field is None:
                available = format_fields_for_display(result.columns)
                errors.append(
                    f"比较字段 '{f.value}' 不存在。可用字段: {available}"
                )
                continue

            right_col = result[right_field]
            if not pd.api.types.is_numeric_dtype(right_col):
                numeric_fields = format_fields_for_display(
                    [c for c in result.columns if pd.api.types.is_numeric_dtype(result[c])]
                )
                errors.append(
                    f"比较字段 '{f.value}' 不是数值字段。可筛选字段: {numeric_fields}"
                )
                continue

            mask = left_col.notna() & right_col.notna() & op_func(left_col, right_col)
        else:
            mask = left_col.notna() & op_func(left_col, f.value)
        result = result[mask]

    return result, errors

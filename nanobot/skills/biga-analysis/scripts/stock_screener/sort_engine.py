"""Sort engine - parse sort expressions and apply multi-field sorting."""

import re
from dataclasses import dataclass

import pandas as pd

try:
    from .field_metadata import format_fields_for_display, resolve_field_name
except ImportError:
    from field_metadata import format_fields_for_display, resolve_field_name


SORT_PATTERN = re.compile(r"^([^\s]+)\s+(asc|desc)$", re.IGNORECASE)


@dataclass
class Sort:
    """A single sort directive: field + direction."""

    field: str
    ascending: bool

    def __str__(self) -> str:
        return f"{self.field} {'asc' if self.ascending else 'desc'}"


def parse_sort(expr: str) -> Sort:
    """Parse a string like 'roe desc' into a Sort."""
    if not isinstance(expr, str):
        raise ValueError(f"排序条件必须是字符串，收到: {type(expr).__name__}")

    expr = expr.strip()
    match = SORT_PATTERN.match(expr)
    if not match:
        raise ValueError(
            f"无法解析排序条件: '{expr}'\n"
            "正确格式: 'field asc' 或 'field desc'，例如 'roe desc'"
        )

    return Sort(
        field=match.group(1),
        ascending=(match.group(2).lower() == "asc"),
    )


def apply_sorts(df: pd.DataFrame, sorts: list[Sort]) -> tuple[pd.DataFrame, list[str]]:
    """Apply multi-field sorting.

    The first sort field has the highest priority.
    """
    errors: list[str] = []
    valid: list[Sort] = []

    for item in sorts:
        field = resolve_field_name(item.field, df.columns)
        if field is None:
            available = format_fields_for_display(df.columns)
            errors.append(f"排序字段 '{item.field}' 不存在。可用字段: {available}")
            continue
        valid.append(Sort(field=field, ascending=item.ascending))

    if not valid:
        return df, errors

    fields = [item.field for item in valid]
    ascending = [item.ascending for item in valid]
    result = df.sort_values(by=fields, ascending=ascending, na_position="last")
    return result, errors

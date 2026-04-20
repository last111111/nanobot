"""
stock_screener — A股股票筛选工具包

可作为命令行工具使用:
    python -m stock_screener.main --data stocks.csv --filter "pe < 20"

也可作为 Python 库 import:
    from stock_screener.loader import load_csv
    from stock_screener.filter_engine import parse_filter, apply_filters
    from stock_screener.sort_engine import parse_sort, apply_sorts
    from stock_screener.formatter import format_table, format_json
"""

from .loader import load_csv, get_numeric_columns, get_all_columns
from .filter_engine import Filter, parse_filter, apply_filters
from .sort_engine import Sort, parse_sort, apply_sorts
from .formatter import format_table, format_json, format_error

__all__ = [
    "load_csv",
    "get_numeric_columns",
    "get_all_columns",
    "Filter",
    "parse_filter",
    "apply_filters",
    "Sort",
    "parse_sort",
    "apply_sorts",
    "format_table",
    "format_json",
    "format_error",
]

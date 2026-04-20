#!/usr/bin/env python3
"""
股票筛选工具 - Agent/LLM 友好的命令行接口

支持多条件筛选、多字段排序、table/json 输出。
可通过 --filter/--sort 参数逐条传入，也可通过 --query 传入 JSON 一次性指定。
"""

import argparse
import json
import os
import sys

if __package__:
    from .field_metadata import (
        build_field_catalog,
        format_fields_for_display,
        get_field_label,
        get_strategy_examples,
        resolve_field_name,
    )
    from .filter_engine import OPERATOR_DESCRIPTIONS, apply_filters, parse_filter
    from .formatter import format_error, format_json, format_table
    from .loader import get_all_columns, get_numeric_columns, load_csv
    from .sort_engine import apply_sorts, parse_sort
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from field_metadata import (
        build_field_catalog,
        format_fields_for_display,
        get_field_label,
        get_strategy_examples,
        resolve_field_name,
    )
    from filter_engine import OPERATOR_DESCRIPTIONS, apply_filters, parse_filter
    from formatter import format_error, format_json, format_table
    from loader import get_all_columns, get_numeric_columns, load_csv
    from sort_engine import apply_sorts, parse_sort


VALID_OUTPUT_FORMATS = {"table", "json"}
ALLOWED_QUERY_KEYS = {"filters", "sort", "columns", "limit", "output"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="股票筛选工具 - 支持多条件筛选与排序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --data stocks.csv --filter "pe < 20" --sort "roe desc"
  %(prog)s --data stocks.csv --filter "现价 > 月30均线" --filter "现价 > 月60均线"
  %(prog)s --data stocks.csv --query '{"filters":["pe < 20"],"sort":["roe desc"],"limit":10}'
  %(prog)s --data stocks.csv --list-columns
  %(prog)s --data stocks.csv --list-filters
""",
    )

    parser.add_argument("--data", required=True, help="CSV 数据文件路径")
    parser.add_argument(
        "--filter",
        action="append",
        dest="filters",
        default=[],
        help="筛选条件，格式: 'field op value'。可多次使用。例: --filter 'pe < 20'",
    )
    parser.add_argument(
        "--sort",
        action="append",
        dest="sorts",
        default=[],
        help="排序条件，格式: 'field asc|desc'。可多次使用（先出现 = 优先级高）。",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help='JSON 格式统一查询，格式: \'{"filters":["pe < 20"],"sort":["roe desc"],"columns":["code"],"limit":10}\'',
    )
    parser.add_argument(
        "--output",
        choices=sorted(VALID_OUTPUT_FORMATS),
        default="table",
        help="输出格式: table（默认）或 json",
    )
    parser.add_argument("--columns", type=str, default=None, help="输出列，逗号分隔。")
    parser.add_argument("--limit", type=int, default=0, help="限制输出行数（0 = 全部）")
    parser.add_argument("--list-columns", action="store_true", help="列出数据文件中所有可用字段后退出")
    parser.add_argument("--list-filters", action="store_true", help="列出可筛选字段、运算符和示例后退出")
    return parser


def merge_query(args) -> None:
    """Merge --query JSON into args.filters / args.sorts / etc."""
    if not args.query:
        return

    try:
        query = json.loads(args.query)
    except json.JSONDecodeError as e:
        raise ValueError(f"--query JSON 解析失败: {e}")

    if not isinstance(query, dict):
        raise ValueError("--query 必须是 JSON 对象，例如 {\"filters\":[\"pe < 20\"]}")

    if "output" in query:
        if query["output"] not in VALID_OUTPUT_FORMATS:
            choices = ", ".join(sorted(VALID_OUTPUT_FORMATS))
            raise ValueError(f"query.output 必须是以下之一: {choices}")
        args.output = query["output"]

    unknown_keys = sorted(set(query) - ALLOWED_QUERY_KEYS)
    if unknown_keys:
        allowed = ", ".join(sorted(ALLOWED_QUERY_KEYS))
        raise ValueError(f"--query 存在未知字段: {unknown_keys}。允许字段: {allowed}")

    if "filters" in query:
        if not isinstance(query["filters"], list):
            raise ValueError("query.filters 必须是数组")
        if any(not isinstance(item, str) for item in query["filters"]):
            raise ValueError("query.filters 的每一项都必须是字符串")
        args.filters.extend(query["filters"])

    if "sort" in query:
        if not isinstance(query["sort"], list):
            raise ValueError("query.sort 必须是数组")
        if any(not isinstance(item, str) for item in query["sort"]):
            raise ValueError("query.sort 的每一项都必须是字符串")
        args.sorts.extend(query["sort"])

    if "columns" in query:
        if isinstance(query["columns"], list):
            if any(not isinstance(item, str) for item in query["columns"]):
                raise ValueError("query.columns 的每一项都必须是字符串")
            args.columns = ",".join(query["columns"])
        elif isinstance(query["columns"], str):
            args.columns = query["columns"]
        else:
            raise ValueError("query.columns 必须是字符串或字符串数组")

    if "limit" in query:
        try:
            args.limit = int(query["limit"])
        except (TypeError, ValueError) as e:
            raise ValueError(f"query.limit 必须是整数: {e}")


def _format_columns_listing(df, data_path: str, output_format: str) -> str:
    all_cols = get_all_columns(df)
    num_cols = get_numeric_columns(df)
    catalog = build_field_catalog(df)

    if output_format == "json":
        return json.dumps(
            {
                "all_columns": all_cols,
                "numeric_columns": num_cols,
                "field_catalog": catalog,
                "row_count": len(df),
            },
            ensure_ascii=False,
            indent=2,
        )

    lines = [
        f"数据文件: {data_path}",
        f"总行数: {len(df)}",
        "",
        "可用字段:",
        f"  {'字段名':<18} {'中文名':<14} {'类型':<8} {'说明':<18}",
        f"  {'-' * 66}",
    ]
    for item in catalog:
        lines.append(
            f"  {str(item['field']):<18} {str(item['label']):<14} "
            f"{str(item['type']):<8} {str(item['description']):<18}"
        )
    lines.append("")
    lines.append(f"数值字段（可筛选/排序）: {format_fields_for_display(num_cols)}")
    return "\n".join(lines)


def _format_filters_listing(df, data_path: str, output_format: str) -> str:
    num_cols = get_numeric_columns(df)
    ops = [{"op": op, "description": OPERATOR_DESCRIPTIONS[op]} for op in OPERATOR_DESCRIPTIONS]
    strategy_examples = get_strategy_examples()

    if output_format == "json":
        fields = []
        for col in num_cols:
            series = df[col]
            fields.append(
                {
                    "field": col,
                    "label": get_field_label(col),
                    "min": round(float(series.min()), 4) if series.notna().any() else None,
                    "max": round(float(series.max()), 4) if series.notna().any() else None,
                    "mean": round(float(series.mean()), 4) if series.notna().any() else None,
                    "null_count": int(series.isna().sum()),
                }
            )
        return json.dumps(
            {
                "data_file": data_path,
                "row_count": len(df),
                "filterable_fields": fields,
                "operators": ops,
                "sort_directions": ["asc", "desc"],
                "examples": [
                    '--filter "pe < 20"',
                    '--filter "roe > 15"',
                    '--sort "market_cap desc"',
                    '--filter "现价 > 月30均线" --filter "现价 > 月60均线"',
                ],
                "strategy_examples": strategy_examples,
            },
            ensure_ascii=False,
            indent=2,
        )

    lines = [
        f"数据文件: {data_path}（{len(df)} 行）",
        "",
        "可筛选/排序字段:",
        f"  {'字段名':<18} {'中文名':<14} {'最小值':>10} {'最大值':>10} {'平均值':>10} {'空值数':>6}",
        f"  {'-' * 76}",
    ]
    for col in num_cols:
        series = df[col]
        na = int(series.isna().sum())
        if series.notna().any():
            lo = f"{series.min():.2f}"
            hi = f"{series.max():.2f}"
            avg = f"{series.mean():.2f}"
        else:
            lo = "-"
            hi = "-"
            avg = "-"
        na_str = str(na) if na > 0 else ""
        lines.append(
            f"  {col:<18} {get_field_label(col):<14} {lo:>10} {hi:>10} {avg:>10} {na_str:>6}"
        )

    lines.extend(
        [
            "",
            "支持的运算符:",
            *[f"  {op:<6} {desc}" for op, desc in OPERATOR_DESCRIPTIONS.items()],
            "",
            "排序方向: asc（升序）, desc（降序）",
            "",
            "示例:",
            '  --filter "pe < 20"',
            '  --filter "roe > 15" --sort "market_cap desc"',
            '  --filter "现价 > 月30均线" --filter "现价 > 月60均线"',
            "",
            "策略示例:",
        ]
    )
    for strategy in strategy_examples:
        filters = " --filter ".join(f'"{expr}"' for expr in strategy["filters"])
        lines.append(f"  {strategy['name']}: {strategy['description']}")
        lines.append(f"    --filter {filters}")
    return "\n".join(lines)


def _resolve_output_columns(columns_arg: str | None, df) -> list[str] | None:
    if not columns_arg:
        return None

    requested = [col.strip() for col in columns_arg.split(",") if col.strip()]
    resolved_columns: list[str] = []
    missing: list[str] = []

    for col in requested:
        resolved = resolve_field_name(col, df.columns)
        if resolved is None:
            missing.append(col)
            continue
        if resolved not in resolved_columns:
            resolved_columns.append(resolved)

    if missing:
        available = format_fields_for_display(df.columns)
        raise ValueError(f"输出列 {missing} 不存在。可用字段: {available}")

    return resolved_columns


def run(args) -> int:
    """Core logic - returns exit code (0=success, 1=error)."""
    initial_fmt = args.output

    try:
        merge_query(args)
    except ValueError as e:
        fmt = args.output if args.output in VALID_OUTPUT_FORMATS else initial_fmt
        print(format_error(str(e), fmt), file=sys.stderr)
        return 1

    fmt = args.output

    try:
        df = load_csv(args.data)
    except (FileNotFoundError, ValueError) as e:
        print(format_error(str(e), fmt), file=sys.stderr)
        return 1

    if args.list_columns:
        print(_format_columns_listing(df, args.data, fmt))
        return 0

    if args.list_filters:
        print(_format_filters_listing(df, args.data, fmt))
        return 0

    filters = []
    for expr in args.filters:
        try:
            filters.append(parse_filter(expr))
        except ValueError as e:
            print(format_error(str(e), fmt), file=sys.stderr)
            return 1

    sorts = []
    for expr in args.sorts:
        try:
            sorts.append(parse_sort(expr))
        except ValueError as e:
            print(format_error(str(e), fmt), file=sys.stderr)
            return 1

    all_errors: list[str] = []
    if filters:
        df, errs = apply_filters(df, filters)
        all_errors.extend(errs)

    if sorts:
        df, errs = apply_sorts(df, sorts)
        all_errors.extend(errs)

    if all_errors:
        for err in all_errors:
            print(format_error(err, fmt), file=sys.stderr)
        return 1

    if args.limit > 0:
        df = df.head(args.limit)

    try:
        columns = _resolve_output_columns(args.columns, df)
    except ValueError as e:
        print(format_error(str(e), fmt), file=sys.stderr)
        return 1

    if fmt == "json":
        print(format_json(df, columns))
    else:
        print(format_table(df, columns))

    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()

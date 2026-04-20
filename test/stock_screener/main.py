#!/usr/bin/env python3
"""
股票筛选工具 — Agent/LLM 友好的命令行接口

支持多条件筛选、多字段排序、table/json 输出。
可通过 --filter/--sort 参数逐条传入，也可通过 --query 传入 JSON 一次性指定。

用法示例:
    python main.py --data stocks.csv --filter "pe < 20" --sort "roe desc"
    python main.py --data stocks.csv --query '{"filters":["pe<20","roe>10"],"sort":["market_cap desc"]}'
"""

import argparse
import json
import os
import sys

if __package__:
    from .field_metadata import (
        build_field_catalog,
        format_field_for_display,
        format_fields_for_display,
        get_field_label,
        get_strategy_examples,
        resolve_field_name,
    )
    from .loader import load_csv, get_numeric_columns, get_all_columns
    from .filter_engine import parse_filter, apply_filters, OPERATOR_DESCRIPTIONS
    from .sort_engine import parse_sort, apply_sorts
    from .formatter import format_table, format_json, format_error
else:
    # Allow running as a standalone script.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from field_metadata import (
        build_field_catalog,
        format_field_for_display,
        format_fields_for_display,
        get_field_label,
        get_strategy_examples,
        resolve_field_name,
    )
    from loader import load_csv, get_numeric_columns, get_all_columns
    from filter_engine import parse_filter, apply_filters, OPERATOR_DESCRIPTIONS
    from sort_engine import parse_sort, apply_sorts
    from formatter import format_table, format_json, format_error


VALID_OUTPUT_FORMATS = {"table", "json"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="股票筛选工具 — 支持多条件筛选与排序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 筛选 PE < 20 的股票，按 ROE 降序
  %(prog)s --data stocks.csv --filter "pe < 20" --sort "roe desc"

  # 多条件筛选 + 多字段排序
  %(prog)s --data stocks.csv --filter "roe > 10" --filter "pb < 3" --sort "market_cap desc" --sort "roe asc"

  # JSON 查询（适合 agent/LLM 生成）
  %(prog)s --data stocks.csv --query '{"filters":["pe < 20","roe > 10"],"sort":["roe desc"],"limit":10}'

  # 指定输出列 + JSON 格式
  %(prog)s --data stocks.csv --filter "pe < 15" --columns code,name,pe,roe --output json

  # 列出数据文件的所有可用字段
  %(prog)s --data stocks.csv --list-columns
""",
    )

    parser.add_argument(
        "--data", required=True,
        help="CSV 数据文件路径",
    )
    parser.add_argument(
        "--filter", action="append", dest="filters", default=[],
        help="筛选条件，格式: 'field op value'。可多次使用。"
             "支持运算符: >, >=, <, <=, ==。例: --filter 'pe < 20'",
    )
    parser.add_argument(
        "--sort", action="append", dest="sorts", default=[],
        help="排序条件，格式: 'field asc|desc'。可多次使用（先出现 = 优先级高）。"
             "例: --sort 'roe desc'",
    )
    parser.add_argument(
        "--query", type=str, default=None,
        help='JSON 格式统一查询，替代多个 --filter/--sort。'
             '格式: \'{"filters":["pe < 20"],"sort":["roe desc"],"columns":["code","name"],"limit":10}\'',
    )
    parser.add_argument(
        "--output", choices=["table", "json"], default="table",
        help="输出格式: table（默认，适合人读） 或 json（适合程序解析）",
    )
    parser.add_argument(
        "--columns", type=str, default=None,
        help="输出列，逗号分隔。例: --columns code,name,price,pe",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="限制输出行数（0 = 全部）",
    )
    parser.add_argument(
        "--list-columns", action="store_true",
        help="列出数据文件中所有可用字段后退出",
    )
    parser.add_argument(
        "--list-filters", action="store_true",
        help="列出所有可筛选字段、值范围、运算符和示例后退出",
    )

    return parser


def merge_query(args):
    """Merge --query JSON into args.filters / args.sorts / etc."""
    if not args.query:
        return

    try:
        q = json.loads(args.query)
    except json.JSONDecodeError as e:
        raise ValueError(f"--query JSON 解析失败: {e}")

    if not isinstance(q, dict):
        raise ValueError("--query 必须是 JSON 对象，例如 {\"filters\":[\"pe < 20\"]}")

    if "output" in q:
        if q["output"] not in VALID_OUTPUT_FORMATS:
            choices = ", ".join(sorted(VALID_OUTPUT_FORMATS))
            raise ValueError(f"query.output 必须是以下之一: {choices}")
        args.output = q["output"]

    if "filters" in q:
        if not isinstance(q["filters"], list):
            raise ValueError("query.filters 必须是数组")
        if any(not isinstance(item, str) for item in q["filters"]):
            raise ValueError("query.filters 的每一项都必须是字符串")
        args.filters.extend(q["filters"])

    if "sort" in q:
        if not isinstance(q["sort"], list):
            raise ValueError("query.sort 必须是数组")
        if any(not isinstance(item, str) for item in q["sort"]):
            raise ValueError("query.sort 的每一项都必须是字符串")
        args.sorts.extend(q["sort"])

    if "columns" in q:
        if isinstance(q["columns"], list):
            if any(not isinstance(item, str) for item in q["columns"]):
                raise ValueError("query.columns 的每一项都必须是字符串")
            args.columns = ",".join(q["columns"])
        elif isinstance(q["columns"], str):
            args.columns = q["columns"]
        else:
            raise ValueError("query.columns 必须是字符串或字符串数组")

    if "limit" in q:
        try:
            args.limit = int(q["limit"])
        except (TypeError, ValueError) as e:
            raise ValueError(f"query.limit 必须是整数: {e}")


def run(args) -> int:
    """Core logic — returns exit code (0=success, 1=error)."""
    initial_fmt = args.output

    # 1. Merge --query JSON first so query.output affects every code path.
    try:
        merge_query(args)
    except ValueError as e:
        fmt = args.output if args.output in VALID_OUTPUT_FORMATS else initial_fmt
        print(format_error(str(e), fmt), file=sys.stderr)
        return 1

    fmt = args.output

    # 2. Load data
    try:
        df = load_csv(args.data)
    except (FileNotFoundError, ValueError) as e:
        print(format_error(str(e), fmt), file=sys.stderr)
        return 1

    # 3. --list-columns: print columns and exit
    if args.list_columns:
        all_cols = get_all_columns(df)
        num_cols = get_numeric_columns(df)
        catalog = build_field_catalog(df)
        if fmt == "json":
            info = {
                "all_columns": all_cols,
                "numeric_columns": num_cols,
                "field_catalog": catalog,
                "row_count": len(df),
            }
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print(f"数据文件: {args.data}")
            print(f"总行数: {len(df)}")
            print("\n可用字段:")
            print(f"  {'字段名':<18} {'中文名':<14} {'类型':<8} {'说明':<18}")
            print(f"  {'-' * 66}")
            for item in catalog:
                print(
                    f"  {str(item['field']):<18} {str(item['label']):<14} "
                    f"{str(item['type']):<8} {str(item['description']):<18}"
                )
            print(f"\n数值字段（可筛选/排序）: {format_fields_for_display(num_cols)}")
        return 0

    # 3b. --list-filters: show filterable fields with stats, operators, examples
    if args.list_filters:
        num_cols = get_numeric_columns(df)
        ops = [{"op": op, "description": OPERATOR_DESCRIPTIONS[op]} for op in OPERATOR_DESCRIPTIONS]
        strategy_examples = get_strategy_examples()

        if fmt == "json":
            fields = []
            for col in num_cols:
                s = df[col]
                fields.append({
                    "field": col,
                    "label": get_field_label(col),
                    "min": round(float(s.min()), 4) if s.notna().any() else None,
                    "max": round(float(s.max()), 4) if s.notna().any() else None,
                    "mean": round(float(s.mean()), 4) if s.notna().any() else None,
                    "null_count": int(s.isna().sum()),
                })
            info = {
                "filterable_fields": fields,
                "operators": ops,
                "sort_directions": ["asc", "desc"],
                "row_count": len(df),
                "examples": [
                    '--filter "pe < 20"',
                    '--filter "roe > 15"',
                    '--sort "market_cap desc"',
                    '--filter "现价 > 月30均线" --filter "现价 > 月60均线"',
                    '--query \'{"filters":["pe < 20","roe > 10"],"sort":["roe desc"]}\'',
                ],
                "strategy_examples": strategy_examples,
            }
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print(f"数据文件: {args.data}（{len(df)} 行）\n")
            print("可筛选/排序字段:")
            print(
                f"  {'字段名':<18} {'中文名':<14} {'最小值':>10} {'最大值':>10} "
                f"{'平均值':>10} {'空值数':>6}"
            )
            print(f"  {'-'*76}")
            for col in num_cols:
                s = df[col]
                na = int(s.isna().sum())
                if s.notna().any():
                    lo = f"{s.min():.2f}"
                    hi = f"{s.max():.2f}"
                    avg = f"{s.mean():.2f}"
                else:
                    lo = hi = avg = "-"
                na_str = str(na) if na > 0 else ""
                print(
                    f"  {col:<18} {get_field_label(col):<14} "
                    f"{lo:>10} {hi:>10} {avg:>10} {na_str:>6}"
                )

            print(f"\n支持的运算符:")
            for op, desc in OPERATOR_DESCRIPTIONS.items():
                print(f"  {op:<6} {desc}")

            print(f"\n排序方向: asc（升序）, desc（降序）")

            print(f"\n示例:")
            print(f'  --filter "pe < 20"')
            print(f'  --filter "roe > 15" --sort "market_cap desc"')
            print(f'  --filter "现价 > 月30均线" --filter "现价 > 月60均线"')
            print(f'  --query \'{{"filters":["pe < 20"],"sort":["roe desc"]}}\'')

            print(f"\n策略示例:")
            for strategy in strategy_examples:
                filters = " --filter ".join(f'"{expr}"' for expr in strategy["filters"])
                print(f"  {strategy['name']}: {strategy['description']}")
                print(f"    --filter {filters}")
        return 0

    # 4. Parse filters
    filters = []
    for expr in args.filters:
        try:
            filters.append(parse_filter(expr))
        except ValueError as e:
            print(format_error(str(e), fmt), file=sys.stderr)
            return 1

    # 5. Parse sorts
    sorts = []
    for expr in args.sorts:
        try:
            sorts.append(parse_sort(expr))
        except ValueError as e:
            print(format_error(str(e), fmt), file=sys.stderr)
            return 1

    # 6. Apply filters
    all_errors: list[str] = []

    if filters:
        df, errs = apply_filters(df, filters)
        all_errors.extend(errs)

    # 7. Apply sorts
    if sorts:
        df, errs = apply_sorts(df, sorts)
        all_errors.extend(errs)

    # 8. Field errors are fatal — agent needs clear fail signals
    if all_errors:
        for err in all_errors:
            print(format_error(err, fmt), file=sys.stderr)
        return 1

    # 9. Apply limit
    if args.limit > 0:
        df = df.head(args.limit)

    # 10. Parse columns
    columns = None
    if args.columns:
        requested = [c.strip() for c in args.columns.split(",")]
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
            msg = f"输出列 {missing} 不存在。可用字段: {available}"
            print(format_error(msg, fmt), file=sys.stderr)
            if not resolved_columns:
                return 1
        columns = resolved_columns

    # 11. Output
    if fmt == "json":
        print(format_json(df, columns))
    else:
        print(format_table(df, columns))

    return 0


def main():
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()

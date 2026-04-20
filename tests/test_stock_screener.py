from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "nanobot" / "skills" / "biga-analysis"
STOCK_SCREENER_ROOT = SKILL_ROOT / "scripts" / "stock_screener"
SCREENER_ENTRY = SKILL_ROOT / "scripts" / "screener.py"
DATA_FILE = STOCK_SCREENER_ROOT / "sample_data.csv"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MAIN_MODULE = _load_module(
    "test_stock_screener_main",
    STOCK_SCREENER_ROOT / "main.py",
)


def _run_cli(*argv: str) -> tuple[int, str, str]:
    parser = MAIN_MODULE.build_parser()
    args = parser.parse_args(["--data", str(DATA_FILE), *argv])
    stdout = io.StringIO()
    stderr = io.StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = MAIN_MODULE.run(args)

    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_query_output_json_is_applied_to_normal_results():
    code, stdout, stderr = _run_cli(
        "--query",
        json.dumps(
            {
                "filters": ["pe < 10"],
                "columns": ["code", "name", "pe"],
                "limit": 2,
                "output": "json",
            },
            ensure_ascii=False,
        ),
    )

    assert code == 0
    assert stderr == ""

    payload = json.loads(stdout)
    assert [row["code"] for row in payload] == ["sh601318", "sh600036"]
    assert list(payload[0]) == ["code", "name", "pe"]


def test_query_output_json_is_applied_to_list_columns():
    code, stdout, stderr = _run_cli(
        "--list-columns",
        "--query",
        json.dumps({"output": "json"}, ensure_ascii=False),
    )

    assert code == 0
    assert stderr == ""

    payload = json.loads(stdout)
    assert payload["row_count"] == 30
    assert payload["all_columns"][:2] == ["code", "name"]
    monthly_ma30 = next(item for item in payload["field_catalog"] if item["field"] == "monthly_ma30")
    assert monthly_ma30["label"] == "月30均线"


def test_query_rejects_non_string_filter_items():
    code, stdout, stderr = _run_cli(
        "--query",
        json.dumps({"filters": [123], "output": "json"}, ensure_ascii=False),
    )

    assert code == 1
    assert stdout == ""
    assert json.loads(stderr)["error"] == "query.filters 的每一项都必须是字符串"


def test_query_rejects_unknown_output_format():
    code, stdout, stderr = _run_cli(
        "--output",
        "json",
        "--query",
        json.dumps({"output": "yaml"}, ensure_ascii=False),
    )

    assert code == 1
    assert stdout == ""
    assert "query.output 必须是以下之一" in json.loads(stderr)["error"]


def test_query_rejects_unknown_keys():
    code, stdout, stderr = _run_cli(
        "--query",
        json.dumps({"filters": ["pe < 20"], "srot": ["roe desc"], "output": "json"}, ensure_ascii=False),
    )

    assert code == 1
    assert stdout == ""
    assert "未知字段" in json.loads(stderr)["error"]
    assert "srot" in json.loads(stderr)["error"]


def test_filtering_non_numeric_field_returns_a_clean_error():
    code, stdout, stderr = _run_cli(
        "--output",
        "json",
        "--filter",
        "name > 1",
    )

    assert code == 1
    assert stdout == ""
    error = json.loads(stderr)["error"]
    assert "筛选字段 'name' 不是数值字段" in error
    assert "pe" in error


def test_invalid_output_columns_fail_instead_of_partial_success():
    code, stdout, stderr = _run_cli(
        "--output",
        "json",
        "--columns",
        "代码,不存在字段",
    )

    assert code == 1
    assert stdout == ""
    assert "输出列 ['不存在字段'] 不存在" in json.loads(stderr)["error"]


def test_list_filters_shows_chinese_strategy_example():
    code, stdout, stderr = _run_cli("--list-filters")

    assert code == 0
    assert stderr == ""
    assert "月线长线趋势" in stdout
    assert "月30均线" in stdout
    assert "营收增速" in stdout


def test_chinese_alias_filters_support_field_to_field_comparison():
    code, stdout, stderr = _run_cli(
        "--output",
        "json",
        "--filter",
        "现价 > 月30均线",
        "--filter",
        "现价 > 月60均线",
        "--filter",
        "月30均线 > 月60均线",
        "--filter",
        "营收增速 > 15",
        "--filter",
        "净利润增速 > 15",
        "--sort",
        "净利润增速 desc",
        "--columns",
        "代码,名称,现价,月30均线,月60均线,营收增速,净利润增速",
        "--limit",
        "3",
    )

    assert code == 0
    assert stderr == ""

    payload = json.loads(stdout)
    assert [row["code"] for row in payload] == ["sh688981", "sz300750", "sh600809"]
    assert all(row["price"] > row["monthly_ma30"] > row["monthly_ma60"] for row in payload)


def test_skill_scripts_support_import_stock_screener_package():
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    try:
        import stock_screener  # type: ignore

        assert hasattr(stock_screener, "load_csv")
        assert hasattr(stock_screener, "parse_filter")
    finally:
        sys.path.pop(0)
        sys.modules.pop("stock_screener", None)


def test_screener_wrapper_script_returns_json():
    result = subprocess.run(
        [
            sys.executable,
            str(SCREENER_ENTRY),
            "--data",
            str(DATA_FILE),
            "--output",
            "json",
            "--query",
            json.dumps(
                {
                    "filters": ["现价 > 月30均线", "现价 > 月60均线"],
                    "sort": ["净利润增速 desc"],
                    "columns": ["代码", "名称", "净利润增速"],
                    "limit": 2,
                    "output": "json",
                },
                ensure_ascii=False,
            ),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert [row["code"] for row in payload] == ["sh688981", "sz300750"]

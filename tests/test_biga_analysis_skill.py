from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "nanobot" / "skills" / "biga-analysis"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SKILLS_MODULE = _load_module(
    "test_nanobot_agent_skills",
    REPO_ROOT / "nanobot" / "agent" / "skills.py",
)
SKILL_RUNTIME_MODULE = _load_module(
    "test_nanobot_skill_runtime",
    REPO_ROOT / "nanobot" / "utils" / "skill_runtime.py",
)


def test_biga_analysis_matches_representative_queries():
    loader = SKILLS_MODULE.SkillsLoader(REPO_ROOT)
    queries = [
        "分析一下这只股票：贵州茅台",
        "平安银行是不是超买了",
        "上证指数趋势怎么样",
        "茅台15分钟线怎么看",
        "帮我看看这几只股票",
        "帮我做A股技术分析，看看MACD",
        "按市盈率和ROE帮我筛一下A股",
    ]

    for query in queries:
        assert "biga-analysis" in loader.match_skills(query), query


def test_biga_analysis_active_skill_resolves_runtime_placeholders():
    loader = SKILLS_MODULE.SkillsLoader(REPO_ROOT)
    content = loader.load_skills_for_context(["biga-analysis"])

    assert "{baseDir}" not in content
    assert "{pythonExe}" not in content
    assert str(SKILL_ROOT) in content
    assert sys.executable in content
    assert str(SKILL_ROOT / "scripts" / "screener.py") in content


def test_skill_reference_placeholder_resolution():
    raw = (SKILL_ROOT / "references" / "quick-start.md").read_text(encoding="utf-8")
    content = SKILL_RUNTIME_MODULE.resolve_skill_placeholders(
        raw,
        SKILL_RUNTIME_MODULE.find_skill_root(SKILL_ROOT / "references" / "quick-start.md"),
    )

    assert "{baseDir}" not in content
    assert "{pythonExe}" not in content
    assert str(SKILL_ROOT / "scripts" / "run.py") in content
    assert sys.executable in content


def test_analyze_returns_stable_error_payload(monkeypatch):
    module = _load_module("biga_analysis_run", SKILL_ROOT / "scripts" / "run.py")

    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(module, "get_price", boom)
    result = module.analyze("sh600519", indicators=["MACD"])

    assert result["error"] == "获取行情失败: network down"
    assert result["price"]["code"] == "sh600519"
    assert result["price"]["frequency"] == "1d"
    assert result["indicators"] == {}

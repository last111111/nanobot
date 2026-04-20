"""Field labels, aliases, and strategy examples for the stock screener."""

from __future__ import annotations

import pandas as pd


FIELD_METADATA: dict[str, dict[str, object]] = {
    "code": {
        "label": "代码",
        "description": "股票代码",
        "unit": "",
        "aliases": ["股票代码", "证券代码", "代码"],
    },
    "name": {
        "label": "名称",
        "description": "股票名称",
        "unit": "",
        "aliases": ["股票名称", "名称"],
    },
    "price": {
        "label": "现价",
        "description": "最新价",
        "unit": "元",
        "aliases": ["最新价", "股价", "现价"],
    },
    "pe": {
        "label": "市盈率",
        "description": "PE",
        "unit": "倍",
        "aliases": ["pe", "PE", "市盈率"],
    },
    "pb": {
        "label": "市净率",
        "description": "PB",
        "unit": "倍",
        "aliases": ["pb", "PB", "市净率"],
    },
    "roe": {
        "label": "净资产收益率",
        "description": "ROE",
        "unit": "%",
        "aliases": ["roe", "ROE", "净资产收益率"],
    },
    "market_cap": {
        "label": "总市值",
        "description": "公司总市值",
        "unit": "亿元",
        "aliases": ["市值", "总市值"],
    },
    "volume": {
        "label": "成交量",
        "description": "成交量",
        "unit": "手",
        "aliases": ["成交量", "量"],
    },
    "turnover_rate": {
        "label": "换手率",
        "description": "换手率",
        "unit": "%",
        "aliases": ["换手率"],
    },
    "dividend_yield": {
        "label": "股息率",
        "description": "股息率",
        "unit": "%",
        "aliases": ["股息率", "分红率"],
    },
    "monthly_ma20": {
        "label": "月20均线",
        "description": "20月移动平均线",
        "unit": "元",
        "aliases": ["月20线", "20月线", "月20均线"],
    },
    "monthly_ma30": {
        "label": "月30均线",
        "description": "30月移动平均线",
        "unit": "元",
        "aliases": ["月30线", "30月线", "月30均线"],
    },
    "monthly_ma60": {
        "label": "月60均线",
        "description": "60月移动平均线",
        "unit": "元",
        "aliases": ["月60线", "60月线", "月60均线"],
    },
    "revenue_growth": {
        "label": "营收增速",
        "description": "营业收入同比增速",
        "unit": "%",
        "aliases": ["营收增长", "营收增速", "收入增速"],
    },
    "profit_growth": {
        "label": "净利润增速",
        "description": "归母净利润同比增速",
        "unit": "%",
        "aliases": ["利润增速", "净利润增长", "净利润增速"],
    },
}


STRATEGY_EXAMPLES = [
    {
        "name": "月线长线趋势",
        "description": "股价站上月30和月60均线，且月30均线高于月60均线。",
        "filters": [
            "现价 > 月30均线",
            "现价 > 月60均线",
            "月30均线 > 月60均线",
        ],
    },
    {
        "name": "趋势加业绩",
        "description": "长期趋势成立，再叠加营收和利润增速。",
        "filters": [
            "现价 > 月30均线",
            "现价 > 月60均线",
            "营收增速 > 15",
            "净利润增速 > 15",
        ],
    },
]


def get_field_label(field: str) -> str:
    meta = FIELD_METADATA.get(field, {})
    return str(meta.get("label", field))


def get_field_description(field: str) -> str:
    meta = FIELD_METADATA.get(field, {})
    return str(meta.get("description", ""))


def get_field_unit(field: str) -> str:
    meta = FIELD_METADATA.get(field, {})
    return str(meta.get("unit", ""))


def get_field_aliases(field: str) -> list[str]:
    meta = FIELD_METADATA.get(field, {})
    aliases = meta.get("aliases", [])
    return list(aliases) if isinstance(aliases, list) else []


def resolve_field_name(name: str, columns: list[str] | pd.Index) -> str | None:
    available = list(columns)
    if name in available:
        return name

    alias_map: dict[str, str] = {}
    for field in available:
        candidates = {field, field.lower(), get_field_label(field)}
        for alias in get_field_aliases(field):
            candidates.add(alias)
            candidates.add(alias.lower())
        for candidate in candidates:
            alias_map[candidate] = field

    return alias_map.get(name) or alias_map.get(name.lower())


def build_field_catalog(df: pd.DataFrame) -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []
    for field in df.columns:
        catalog.append(
            {
                "field": field,
                "label": get_field_label(field),
                "description": get_field_description(field),
                "unit": get_field_unit(field),
                "type": "numeric" if pd.api.types.is_numeric_dtype(df[field]) else "text",
                "aliases": get_field_aliases(field),
            }
        )
    return catalog


def format_field_for_display(field: str) -> str:
    label = get_field_label(field)
    if label == field:
        return field
    return f"{field}（{label}）"


def format_fields_for_display(fields: list[str] | pd.Index) -> str:
    return ", ".join(format_field_for_display(field) for field in fields)


def get_strategy_examples() -> list[dict[str, object]]:
    return [dict(item) for item in STRATEGY_EXAMPLES]

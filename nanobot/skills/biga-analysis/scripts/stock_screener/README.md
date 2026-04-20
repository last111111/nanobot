# stock_screener - A股股票筛选工具

面向 agent / LLM 的命令行股票筛选器，支持多条件筛选、多字段排序、`table` / `json` 输出，并支持中文字段别名。

## 目录结构

```text
stock_screener/
├── __init__.py
├── main.py
├── loader.py
├── filter_engine.py
├── sort_engine.py
├── formatter.py
├── field_metadata.py
├── sample_data.csv
└── README.md
```

## 快速开始

```bash
cd nanobot/skills/biga-analysis/scripts/stock_screener

# 查看字段
python main.py --data sample_data.csv --list-columns

# 查看筛选能力和策略示例
python main.py --data sample_data.csv --list-filters

# 基础筛选
python main.py --data sample_data.csv --filter "pe < 20" --sort "roe desc"

# 中文条件：月线长线趋势
python main.py --data sample_data.csv \
  --filter "现价 > 月30均线" \
  --filter "现价 > 月60均线" \
  --filter "月30均线 > 月60均线"
```

## CLI 设计

- `--filter`：可重复，统一使用 `field op value`
- `--sort`：可重复，统一使用 `field asc|desc`
- `--query`：结构化 JSON，一次传入所有筛选、排序和输出参数
- `--output json`：稳定机器可解析输出
- `--list-columns` / `--list-filters`：先发现字段，再生成查询

这套设计对 LLM 更友好，因为：

- 命令格式固定，便于模板化生成
- 规则简单，没有隐式优先级
- 错误信息清晰，适合自动重试
- `--query` 可以作为统一结构化接口

## 支持字段

基础指标：

- `price`
- `pe`
- `pb`
- `roe`
- `market_cap`
- `volume`

补充字段：

- `turnover_rate`
- `dividend_yield`
- `monthly_ma20`
- `monthly_ma30`
- `monthly_ma60`
- `revenue_growth`
- `profit_growth`

常用中文别名：

- `现价` -> `price`
- `市盈率` -> `pe`
- `市净率` -> `pb`
- `净资产收益率` -> `roe`
- `总市值` -> `market_cap`
- `成交量` -> `volume`
- `月30均线` -> `monthly_ma30`
- `月60均线` -> `monthly_ma60`
- `营收增速` -> `revenue_growth`
- `净利润增速` -> `profit_growth`

## 筛选规则

格式：

```text
field op value
```

支持运算符：

- `>`
- `>=`
- `<`
- `<=`
- `==`

支持两种比较：

```bash
--filter "pe < 20"
--filter "现价 > 月30均线"
```

多个 `--filter` 之间是 AND 关系，按顺序执行。

## 排序规则

格式：

```text
field asc|desc
```

- `asc`：升序
- `desc`：降序

多个 `--sort` 按出现顺序决定优先级，第一个字段优先级最高。

```bash
--sort "market_cap desc" --sort "roe asc"
```

## JSON 查询模式

```bash
python main.py --data sample_data.csv --query '{
  "filters": ["现价 > 月30均线", "现价 > 月60均线"],
  "sort": ["净利润增速 desc"],
  "columns": ["代码", "名称", "现价", "净利润增速"],
  "limit": 5,
  "output": "json"
}'
```

允许的 `query` 字段只有：

- `filters`
- `sort`
- `columns`
- `limit`
- `output`

未知字段会直接报错，避免 LLM 拼错参数后被静默忽略。

## 错误处理

以下情况会返回清晰错误并退出码为 `1`：

- CSV 文件不存在
- CSV 文件为空或无法读取
- 指标名不存在
- 运算符非法
- 排序方向非法
- `--query` 中出现未知字段
- 输出列不存在
- 非数值字段参与数值筛选

`json` 模式下错误格式固定为：

```json
{
  "error": "具体错误信息"
}
```

## 示例输出

### table

```text
      代码   名称     现价  月30均线  月60均线  净利润增速
sh688981 中芯国际   48.5   42.0   38.0   26.0
sz300750 宁德时代  182.5  166.0  148.0   24.0
sh600809 山西汾酒  218.5  188.0  160.0   22.0
```

### json

```json
[
  {
    "code": "sh688981",
    "name": "中芯国际",
    "price": 48.5,
    "monthly_ma30": 42.0,
    "monthly_ma60": 38.0,
    "profit_growth": 26.0
  }
]
```

## 作为 Python 库使用

```python
from pathlib import Path
import sys

skill_scripts = Path("nanobot/skills/biga-analysis/scripts")
sys.path.insert(0, str(skill_scripts))

from stock_screener.loader import load_csv
from stock_screener.filter_engine import parse_filter, apply_filters
from stock_screener.sort_engine import parse_sort, apply_sorts

df = load_csv("nanobot/skills/biga-analysis/scripts/stock_screener/sample_data.csv")
filters = [parse_filter("现价 > 月30均线"), parse_filter("净利润增速 > 15")]
df, errors = apply_filters(df, filters)
sorts = [parse_sort("净利润增速 desc")]
df, errors = apply_sorts(df, sorts)
```

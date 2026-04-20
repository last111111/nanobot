# stock_screener — A股股票筛选工具

Agent/LLM 友好的命令行股票筛选器，支持多条件筛选、多字段排序、table/JSON 输出。
支持英文内部字段和中文别名，适合把选股思路直接翻成命令行条件。

## 目录结构

```
test/stock_screener/
├── main.py            # CLI 入口
├── loader.py          # 数据加载（CSV）
├── filter_engine.py   # 筛选条件解析与执行
├── sort_engine.py     # 排序条件解析与执行
├── formatter.py       # 输出格式化（table / json）
├── __init__.py        # 包入口，暴露公共 API
├── sample_data.csv    # 示例数据（30只A股）
└── README.md          # 本文件
```

## 快速开始

```bash
cd test/stock_screener

# 查看可用字段
python main.py --data sample_data.csv --list-columns

# 查看可筛选字段和策略示例
python main.py --data sample_data.csv --list-filters

# 筛选 PE < 20 的股票
python main.py --data sample_data.csv --filter "pe < 20"

# 多条件筛选 + 排序
python main.py --data sample_data.csv --filter "pe < 20" --filter "roe > 10" --sort "roe desc"

# 中文条件：月线长线趋势
python main.py --data sample_data.csv \
  --filter "现价 > 月30均线" \
  --filter "现价 > 月60均线" \
  --filter "月30均线 > 月60均线"
```

## CLI 参数

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--data` | 是 | CSV 数据文件路径 | `--data stocks.csv` |
| `--filter` | 否 | 筛选条件，可多次使用 | `--filter "pe < 20"` |
| `--sort` | 否 | 排序条件，可多次使用 | `--sort "roe desc"` |
| `--query` | 否 | JSON 格式统一查询 | `--query '{"filters":["pe<20"]}'` |
| `--output` | 否 | 输出格式: `table`(默认) / `json` | `--output json` |
| `--columns` | 否 | 输出列，逗号分隔 | `--columns code,name,pe` |
| `--limit` | 否 | 限制输出行数 (0=全部) | `--limit 10` |
| `--list-columns` | 否 | 列出所有可用字段后退出 | |
| `--list-filters` | 否 | 列出可筛选字段、值范围、运算符和示例后退出 | |

## 筛选规则

### 格式
```
field op value
```

`field` 和右侧的 `value` 都可以是字段名，因此既支持：

```bash
--filter "pe < 20"
--filter "price > monthly_ma30"
--filter "现价 > 月30均线"
```

### 支持的运算符
| 运算符 | 含义 | 示例 |
|--------|------|------|
| `>` | 大于 | `pe > 10` |
| `>=` | 大于等于 | `roe >= 15` |
| `<` | 小于 | `pb < 3` |
| `<=` | 小于等于 | `pe <= 20` |
| `==` | 等于 | `dividend_yield == 0` |

### 多条件逻辑
多个 `--filter` 之间是 **AND** 关系。筛选按顺序执行，每一步都缩小结果集。

包含 NaN 值的行会被自动排除（不参与比较）。

### 中文字段别名

常用字段可以直接用中文写：

| 内部字段 | 中文名 |
|---------|--------|
| `price` | `现价` |
| `monthly_ma20` | `月20均线` |
| `monthly_ma30` | `月30均线` |
| `monthly_ma60` | `月60均线` |
| `revenue_growth` | `营收增速` |
| `profit_growth` | `净利润增速` |

`--filter`、`--sort`、`--columns` 都支持这些中文别名。

## 排序规则

### 格式
```
field asc|desc
```

- `asc`: 升序（小到大）
- `desc`: 降序（大到小）

### 多字段排序
多个 `--sort` 按出现顺序决定优先级。先出现的字段优先级更高。

```bash
--sort "pe asc" --sort "roe desc"
# 先按 PE 升序，PE 相同时按 ROE 降序
```

NaN 值在排序中始终排在最后。

## JSON 查询模式

`--query` 参数接受一个 JSON 对象，适合 agent/LLM 程序化生成：

```bash
python main.py --data stocks.csv --query '{
  "filters": ["pe < 20", "roe > 10"],
  "sort": ["market_cap desc"],
  "columns": ["code", "name", "price", "pe", "roe", "market_cap"],
  "limit": 10,
  "output": "json"
}'
```

JSON 查询中的字段与 CLI 参数含义完全一致，且可以和 CLI 参数混合使用（合并生效）。

## 月线长线选股示例

下面这组条件对应“股价站上月30和月60均线”的长期趋势思路：

```bash
python main.py --data sample_data.csv \
  --filter "现价 > 月30均线" \
  --filter "现价 > 月60均线" \
  --filter "月30均线 > 月60均线" \
  --sort "净利润增速 desc" \
  --columns 代码,名称,现价,月30均线,月60均线,营收增速,净利润增速 \
  --limit 5 \
  --output json
```

如果你还想叠加基本面，可以继续加：

```bash
--filter "营收增速 > 15" --filter "净利润增速 > 15"
```

## 示例输出

### table 格式（默认）
```
$ python main.py --data sample_data.csv --filter "pe < 10" --sort "dividend_yield desc" --columns code,name,pe,roe,dividend_yield

    代码   名称  市盈率  净资产收益率  股息率
sh601288 农业银行  4.90     11.20    6.50
sh601398 工商银行  5.20     11.80    6.20
sz000001 平安银行  5.50     10.50    5.80
sh601166 兴业银行  4.80     12.30    5.60
sh601668 中国建筑  4.20     12.80    4.80
sh601318 中国平安  8.20     14.50    4.20
```

### json 格式
```
$ python main.py --data sample_data.csv --filter "roe > 25" --output json --columns code,name,roe

[
  {"code": "sh600519", "name": "贵州茅台", "roe": 32.1},
  {"code": "sz000858", "name": "五粮液", "roe": 25.6},
  {"code": "sh601899", "name": "紫金矿业", "roe": 28.5},
  {"code": "sh600809", "name": "山西汾酒", "roe": 28.8},
  {"code": "sz000568", "name": "泸州老窖", "roe": 38.5}
]
```

## 错误处理

所有错误信息输出到 stderr，格式与 `--output` 一致：

```bash
# table 模式
错误: 筛选字段 'xxx' 不存在。可用字段: code, name, price, pe, ...

# json 模式
{"error": "筛选字段 'xxx' 不存在。可用字段: code, name, price, pe, ..."}
```

## 作为本目录下模块使用

```python
# 在 test/stock_screener 目录内执行
from loader import load_csv
from filter_engine import parse_filter, apply_filters
from sort_engine import parse_sort, apply_sorts
from formatter import format_json

df = load_csv("sample_data.csv")
filters = [parse_filter("pe < 20"), parse_filter("roe > 10")]
df, errors = apply_filters(df, filters)
sorts = [parse_sort("roe desc")]
df, errors = apply_sorts(df, sorts)
print(format_json(df, columns=["code", "name", "pe", "roe"]))
```

## 支持的指标（sample_data.csv）

| 字段 | 含义 | 单位 |
|------|------|------|
| `code` | 股票代码 | sh600519 格式 |
| `name` | 股票名称 | - |
| `price` | 最新价 | 元 |
| `monthly_ma20` | 20月均线 | 元 |
| `monthly_ma30` | 30月均线 | 元 |
| `monthly_ma60` | 60月均线 | 元 |
| `pe` | 市盈率 | 倍 |
| `pb` | 市净率 | 倍 |
| `roe` | 净资产收益率 | % |
| `revenue_growth` | 营业收入同比增速 | % |
| `profit_growth` | 归母净利润同比增速 | % |
| `market_cap` | 总市值 | 亿元 |
| `volume` | 成交量 | 手 |
| `turnover_rate` | 换手率 | % |
| `dividend_yield` | 股息率 | % |

## 设计说明

### 为什么这样设计 CLI 接口

1. **`--filter` / `--sort` 可重复使用** — 避免复杂的语法解析，每个条件是独立的字符串，LLM 容易生成。

2. **`--query` JSON 模式** — LLM 天然擅长生成 JSON，一次传入所有条件比拼接多个 CLI 参数更不容易出错。

3. **所有错误信息输出到 stderr** — stdout 只包含数据结果，方便管道组合和程序解析。

4. **`--list-columns` 自发现** — Agent 可以先查询有哪些可用字段，再构建查询条件。

5. **`--output json` 结构稳定** — 返回的是标准 JSON 数组，每个元素是同构对象，NaN 转为 null。

### 扩展指南

- **新增指标**: 只需在 CSV 中添加新列，无需修改代码。
- **新增运算符**: 在 `filter_engine.py` 的 `OPERATORS` 字典中添加。
- **新增数据源**: 在 `loader.py` 中添加新的 `load_xxx()` 函数，在 `main.py` 中通过参数选择数据源。
- **新增输出格式**: 在 `formatter.py` 中添加 `format_xxx()` 函数。

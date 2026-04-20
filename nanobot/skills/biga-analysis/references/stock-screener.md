# 股票筛选调用指南

本文档说明 `biga-analysis` skill 中的股票筛选工具如何调用，重点面向 agent / LLM。

## 固定运行约定

- 脚本路径：`{baseDir}/scripts/screener.py`
- Python 解释器：`{pythonExe}`
- 示例数据：`{baseDir}/scripts/stock_screener/sample_data.csv`

## 基本命令模板

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --output json --query '{"filters":["pe < 20"],"sort":["roe desc"],"limit":10}'
```

优先使用 `--output json` 和 `--query`，因为：

- 返回格式稳定
- 参数结构化
- 对 LLM 更容易生成
- 错误信息更容易自动处理

## 何时使用筛选脚本

用户意图包括下面这些时，优先调用筛选脚本：

- “按 PE 从小到大筛一下”
- “找 ROE 大于 15 的股票”
- “按月线趋势选股”
- “帮我做一个条件筛股”
- “把市值大的股票按净利润增速排序”

如果用户是在问单只股票的技术面分析、分钟线、MACD、RSI 等，还是用 `run.py`。

## 推荐工作流

### 1. 先发现字段

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --list-columns --output json
```

返回里会包含：

- `all_columns`
- `numeric_columns`
- `field_catalog`
- `row_count`

### 2. 再发现筛选能力

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --list-filters --output json
```

返回里会包含：

- `filterable_fields`
- `operators`
- `sort_directions`
- `strategy_examples`

### 3. 生成正式查询

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --output json --query '{"filters":["现价 > 月30均线","现价 > 月60均线","月30均线 > 月60均线","净利润增速 > 15"],"sort":["净利润增速 desc"],"columns":["代码","名称","现价","月30均线","月60均线","净利润增速"],"limit":5}'
```

## query 结构

只允许以下字段：

```json
{
  "filters": ["pe < 20"],
  "sort": ["roe desc"],
  "columns": ["代码", "名称", "市盈率"],
  "limit": 10,
  "output": "json"
}
```

注意：

- `filters` 必须是字符串数组
- `sort` 必须是字符串数组
- `columns` 必须是字符串或字符串数组
- `limit` 必须是整数
- 未知字段会直接报错，不会静默忽略

## 条件表达式

筛选格式：

```text
field op value
```

支持运算符：

- `>`
- `>=`
- `<`
- `<=`
- `==`

支持的两种形式：

```text
pe < 20
现价 > 月30均线
```

排序格式：

```text
field asc|desc
```

多个排序字段时，第一个优先级最高。

## 常用中文字段

- `现价`
- `市盈率`
- `市净率`
- `净资产收益率`
- `总市值`
- `成交量`
- `月20均线`
- `月30均线`
- `月60均线`
- `营收增速`
- `净利润增速`

## 常见场景

### 场景 1：基础估值筛选

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --output json --query '{"filters":["pe < 20","roe > 15"],"sort":["roe desc"]}'
```

### 场景 2：月线长线趋势

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --output json --query '{"filters":["现价 > 月30均线","现价 > 月60均线","月30均线 > 月60均线"],"sort":["净利润增速 desc"],"columns":["代码","名称","现价","月30均线","月60均线","净利润增速"],"limit":5}'
```

### 场景 3：趋势加业绩

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --output json --query '{"filters":["现价 > 月30均线","现价 > 月60均线","营收增速 > 15","净利润增速 > 15"],"sort":["净利润增速 desc"]}'
```

## 错误处理

筛选脚本失败时：

- 退出码为 `1`
- `json` 模式下返回：

```json
{
  "error": "具体错误信息"
}
```

常见错误包括：

- CSV 不存在
- 字段不存在
- 非法运算符
- 非法排序方向
- `query` 中存在未知字段
- 输出列不存在

遇到错误时，优先根据错误信息修正参数，而不是猜测继续执行。

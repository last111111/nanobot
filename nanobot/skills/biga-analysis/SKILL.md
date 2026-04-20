---
name: biga-analysis
description: "A股技术分析与股票筛选工具。使用本地脚本获取 A 股/指数/分钟线行情并计算技术指标，或基于本地 CSV 按 PE、PB、ROE、价格、成交量、市值、月线均线等条件筛选股票，返回结构化 JSON。用于股票、个股、大盘、上证、深证、创业板、K线、分钟线、短线、超买超卖、支撑压力、量价、选股、筛股、条件筛选，以及明确提到 MACD、KDJ、RSI、布林带、均线、DMI、OBV、MFI、PE、PB、ROE、市值、成交量等指标的请求。"
metadata: {"nanobot":{"triggers":["分析","A股","股票","个股","大盘","指数","上证","深证","创业板","K线","分钟线","短线","超买","超卖","支撑位","压力位","量价","选股","筛股","筛选","条件筛选","市盈率","市净率","ROE","PE","PB","市值","成交量","MACD","KDJ","RSI","布林带","BOLL","均线","DMI","OBV","MFI"],"requires":{"python_modules":["numpy","pandas","requests"]}}}
---

# A股技术分析

通过本地脚本获取 A 股实时/历史行情，计算技术指标，或基于本地 CSV 执行结构化股票筛选，并以 JSON 返回结果供后续解读。

## 运行时约定

- Python 解释器：`{pythonExe}`
- 技术分析脚本：`{baseDir}/scripts/run.py`
- 股票筛选脚本：`{baseDir}/scripts/screener.py`
- 技术分析标准调用方式：

```bash
"{pythonExe}" "{baseDir}/scripts/run.py" sh600519 -i MACD,RSI,KDJ,BBANDS -j
```

- 股票筛选标准调用方式：

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --output json --query '{"filters":["pe < 20"],"sort":["roe desc"],"limit":10}'
```

- 技术分析始终优先加 `-j/--json`，让返回值保持机器可解析。
- 股票筛选始终优先加 `--output json`，让返回值保持机器可解析。
- 脚本成功时返回：
  - 技术分析：`price` + `indicators`
  - 股票筛选：JSON 数组，或 `--list-columns` / `--list-filters` 的结构化对象
- 脚本失败时也会返回 JSON，包含 `error` 字段；不要依赖 traceback。

## 响应规则

- 向用户展示指标时，必须使用中文名称，不要直接把原始字段名当正文输出。
- 回复里至少说明：
  - 分析对象
  - 周期（如日线、15 分钟线）
  - 数据时间 `price.last_time`
  - 关键结论与依据
- 做完整分析时，要区分：
  - 趋势方向：MACD、DMI
  - 超买超卖：RSI、KDJ、MFI、CCI、WILLR
  - 支撑压力：BBANDS、TAQ、均线
  - 量价验证：OBV、VR、AD/ADOSC
- 涉及投资判断时，结尾加“仅供参考，不构成投资建议”。
- 涉及股票筛选时，优先说明：
  - 使用的数据文件
  - 具体筛选条件
  - 排序规则
  - 返回条数

## 默认工作流

### 1. 单指标查询

用户只问某个或少量指标时，只计算必要指标。

```bash
"{pythonExe}" "{baseDir}/scripts/run.py" sh600519 -i MACD,RSI -j
```

### 2. 完整技术分析

用户问“这只股票/指数怎么样”“趋势如何”“怎么看”时，使用核心指标组合：

```text
MACD,RSI,KDJ,BBANDS,DMI,ATR,OBV,MFI,BRAR
```

### 3. 短线 / 分钟线

用户明确提到分钟线、短线、日内时，改 `--freq` 和 `--count`：

```bash
"{pythonExe}" "{baseDir}/scripts/run.py" sh600519 --freq 15m --count 60 -i MACD,KDJ,RSI,BBANDS -j
```

### 4. 多股票对比

逐个调用脚本，不要把多个代码塞进一次命令里。最后再汇总比较。

### 5. 筛选条件查询（必须自动执行）

用户问"有哪些筛选条件""可以按什么筛选""能筛哪些指标""筛选的指标有哪些""支持哪些条件"等关于可用筛选条件的问题时，**必须立即运行**以下命令，不要凭记忆回答：

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --list-filters --output json
```

拿到 JSON 结果后，**必须面向完全不懂代码的普通用户**用纯自然语言展示。严格遵守以下规则：

**绝对禁止出现的内容：**
- 英文字段名（pe、roe、pb、monthly_ma30、market_cap、asc、desc 等）
- 运算符（>、<、>=、<=、== 等）
- CLI 参数（--filter、--sort、--query、--data、--output 等）
- 文件路径
- 代码片段或命令行示例
- JSON 格式示例
- "样本""样本数据""30 条""数据文件""CSV""记录""行数""row_count"等实现细节——用户不需要知道数据来源、数据量、数据格式
- "数据来源说明"段落——不要向用户解释数据从哪来

**必须使用的展示方式：**
- 用分类方式组织指标：
  - 估值类：市盈率、市净率
  - 盈利类：净资产收益率、营收增速、净利润增速
  - 价格趋势类：现价、月20/30/60均线
  - 交易类：成交量、换手率、总市值
  - 分红类：股息率
- 每个指标只需一句话说明含义，不要展示数值范围、最小值、最大值、平均值等数字
- 最后给出 3-5 个**用户可以直接对你说的自然语言例句**，例如：
  - "帮我找市盈率低于 20 的股票"
  - "筛选净资产收益率大于 15 且股价站上月30均线的"
  - "找出股息率最高的 5 只股票"
  - "哪些股票营收和利润都在增长？"

同理，用户问"有哪些字段""数据里有什么"时，运行：

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --list-columns --output json
```

### 6. 股票筛选

用户问"按 PE/ROE/市值/成交量筛一下""找出符合条件的股票""做一个选股器"时，调用筛选脚本：

```bash
"{pythonExe}" "{baseDir}/scripts/screener.py" --data "{baseDir}/scripts/stock_screener/sample_data.csv" --output json --query '{"filters":["现价 > 月30均线","现价 > 月60均线","净利润增速 > 15"],"sort":["净利润增速 desc"],"columns":["代码","名称","现价","净利润增速"],"limit":5}'
```

如果不确定有哪些可用字段或条件，先运行 `--list-filters` 或 `--list-columns` 查询。

## 证券代码与周期

- 代码支持：
  - `sh600519` / `sz000001`
  - `600519.XSHG` / `000001.XSHE`
- 周期支持：
  - `1d` `1w` `1M`
  - `1m` `5m` `15m` `30m` `60m`

## 何时读取 reference

- 用户问“某个指标怎么理解/公式是什么/怎么看”：

```text
read_file(path="{baseDir}/references/indicators-guide.md")
```

- 用户要做场景化分析、组合调用、回复模板、多股票对比：

```text
read_file(path="{baseDir}/references/quick-start.md")
```

- 用户要做股票筛选、筛股、条件选股、月线均线选股：

```text
read_file(path="{baseDir}/references/stock-screener.md")
```

- 用户只是查一个数值：
  - 不需要额外读 reference，直接跑脚本。

## 注意事项

- 该 skill 面向 A 股，不适用于美股、加密货币或外汇。
- 数据源为新浪财经和腾讯股票免费接口；非交易时段会返回最近交易日数据。
- 股票筛选脚本第一版使用本地 CSV，不直接连接在线行情 API。
- 分钟线数据量有限，长周期指标建议 `count >= 120`。
- 需要当前 Python 环境已安装 `numpy`、`pandas`、`requests`。

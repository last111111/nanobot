# LLM 调用模式与常见场景

本文档面向 LLM agent，说明如何根据用户意图选择脚本参数、处理错误，并组织最终回复。

## 固定运行约定

- 脚本路径：`{baseDir}/scripts/run.py`
- Python 解释器：`{pythonExe}`
- 基本命令模板：

```bash
"{pythonExe}" "{baseDir}/scripts/run.py" <code> -i <INDICATORS> -j
```

## 决策树

```text
用户提问
  ├─ “这只股票/这个指数怎么样” / “做个技术分析”
  │   → 完整分析模式
  ├─ “MACD / RSI / KDJ / 布林带是多少”
  │   → 指定指标模式
  ├─ “是不是超买 / 超卖”
  │   → 超买超卖判断模式
  ├─ “趋势如何 / 多空怎么看”
  │   → 趋势判断模式
  ├─ “15 分钟线 / 短线 / 日内怎么看”
  │   → 分钟线模式
  └─ “比较这几只股票”
      → 多股票对比模式
```

## 通用错误处理

无论哪个场景，都先检查返回码和 `error` 字段：

```python
import json
import subprocess

r = subprocess.run(
    [
        "{pythonExe}",
        "{baseDir}/scripts/run.py",
        "sh600519",
        "-i",
        "MACD,RSI",
        "-j",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
)

data = json.loads(r.stdout) if r.stdout else {}
if r.returncode != 0 or "error" in data:
    error_msg = data.get("error") or r.stderr.strip() or "数据获取失败"
    # 告诉用户数据源暂时不可用、网络异常或代码格式不正确
```

## 场景 1：完整分析

用户例子：
- “分析一下这只股票：贵州茅台”
- “上证指数做个技术面分析”

```python
r = subprocess.run(
    [
        "{pythonExe}",
        "{baseDir}/scripts/run.py",
        "sh600519",
        "-i",
        "MACD,RSI,KDJ,BBANDS,DMI,ATR,OBV,MFI,BRAR",
        "-j",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
data = json.loads(r.stdout)
price = data["price"]
ind = data["indicators"]
```

回复结构：

```text
## {名称} 技术面分析

行情快照：{last_time}，{frequency}，收盘 {close}

趋势判断：
- MACD：DIF={MACD_DIF}，DEA={MACD_DEA}，柱值={MACD_HIST}
- DMI：PDI={DMI_PDI}，MDI={DMI_MDI}，ADX={DMI_ADX}

超买超卖：
- RSI：{RSI}
- KDJ：K={KDJ_K}，D={KDJ_D}，J={KDJ_J}

支撑压力：
- 布林带：上轨 {BBANDS_UPPER}，中轨 {BBANDS_MID}，下轨 {BBANDS_LOWER}

量价验证：
- OBV：{OBV}
- MFI：{MFI}

综合判断：{偏多/偏空/震荡}

仅供参考，不构成投资建议。
```

## 场景 2：指定指标查询

用户例子：
- “这只股票的 MACD 是多少”
- “上证指数 RSI 怎么样”

```python
r = subprocess.run(
    [
        "{pythonExe}",
        "{baseDir}/scripts/run.py",
        "sh600519",
        "-i",
        "MACD",
        "-j",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
data = json.loads(r.stdout)
```

输出策略：
- 直接给数值。
- 用一句话解释信号含义。
- 不要把 `MACD_DIF` 这种字段名原样端给用户。

## 场景 3：超买 / 超卖判断

用户例子：
- “平安银行是不是超买了”
- “这只股票有没有超卖迹象”

```python
r = subprocess.run(
    [
        "{pythonExe}",
        "{baseDir}/scripts/run.py",
        "sz000001",
        "-i",
        "RSI,KDJ,CCI,MFI,WILLR,BBANDS",
        "-j",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
data = json.loads(r.stdout)
ind = data["indicators"]
```

判断建议：
- `RSI > 70` 记 1 个超买信号。
- `KDJ_K > 80` 或 `KDJ_J > 100` 记 1 个超买信号。
- `CCI > 100` 记 1 个超买信号。
- `MFI > 80` 记 1 个超买信号。
- `WILLR > -20` 记 1 个超买信号。

解释规则：
- 3 个及以上：多指标共振，超买/超卖信号较强。
- 2 个：已有明显迹象，但需要结合趋势确认。
- 0 到 1 个：暂无明显超买/超卖。

## 场景 4：趋势判断

用户例子：
- “上证指数趋势怎么样”
- “这只股票现在偏多还是偏空”

```python
r = subprocess.run(
    [
        "{pythonExe}",
        "{baseDir}/scripts/run.py",
        "sh000001",
        "-i",
        "MACD,DMI,ADX,TRIX,BBI,EMA",
        "-j",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
data = json.loads(r.stdout)
```

核心判断：
- `MACD_DIF > MACD_DEA`：偏多。
- `DMI_PDI > DMI_MDI`：上升趋势占优。
- `ADX` 高于 25：趋势更明确。
- 价格高于 BBI / 均线：多方控制更强。

## 场景 5：短线 / 分钟线

用户例子：
- “茅台 15 分钟线怎么看”
- “这只股票短线节奏如何”

```python
r = subprocess.run(
    [
        "{pythonExe}",
        "{baseDir}/scripts/run.py",
        "sh600519",
        "--freq",
        "15m",
        "--count",
        "60",
        "-i",
        "MACD,KDJ,RSI,BBANDS",
        "-j",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
data = json.loads(r.stdout)
```

短线重点：
- KDJ 看拐点。
- MACD 做确认。
- BBANDS 看支撑压力。
- 明确告诉用户这是分钟线结论，不要和日线混写。

## 场景 6：多股票对比

用户例子：
- “帮我看看这几只股票”
- “比较一下茅台和五粮液”

```python
stocks = [("sh600519", "贵州茅台"), ("sz000858", "五粮液")]
results = {}

for code, name in stocks:
    r = subprocess.run(
        [
            "{pythonExe}",
            "{baseDir}/scripts/run.py",
            code,
            "-i",
            "MACD,RSI,KDJ,ATR",
            "-j",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    results[name] = json.loads(r.stdout)
```

对比维度：
- 趋势强弱：MACD、DMI
- 强弱位置：RSI、KDJ
- 波动水平：ATR
- 最后给出谁更强、谁更稳、谁更适合观察

## 场景 7：股票筛选

用户例子：
- “按 PE 和 ROE 筛一下”
- “找出站上月30和月60均线的股票”

```python
r = subprocess.run(
    [
        "{pythonExe}",
        "{baseDir}/scripts/screener.py",
        "--data",
        "{baseDir}/scripts/stock_screener/sample_data.csv",
        "--output",
        "json",
        "--query",
        '{"filters":["现价 > 月30均线","现价 > 月60均线","月30均线 > 月60均线"],"sort":["净利润增速 desc"],"columns":["代码","名称","现价","净利润增速"],"limit":5}',
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
data = json.loads(r.stdout)
```

筛选模式要点：
- 优先使用 `--query`
- 优先使用 `--output json`
- 需要先发现字段时，先跑 `--list-columns` 或 `--list-filters`
- 回复里说明筛选条件和排序逻辑，不要只贴结果

## 常用代码速查

| 代码 | 名称 | 代码 | 名称 |
|------|------|------|------|
| `sh000001` | 上证指数 | `sz399001` | 深证成指 |
| `sz399006` | 创业板指 | `sh000300` | 沪深300 |
| `sh600519` | 贵州茅台 | `sz000858` | 五粮液 |
| `sh601318` | 中国平安 | `sz000001` | 平安银行 |

## 环境说明

- 依赖：`numpy`、`pandas`、`requests`
- 数据源：新浪财经 + 腾讯股票
- 非交易时段返回最近交易日数据

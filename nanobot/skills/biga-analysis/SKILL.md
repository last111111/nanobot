---
name: biga-analysis
description: "A股技术分析工具。通过本地脚本获取A股实时/历史行情并计算34种技术指标(MACD/KDJ/RSI/布林带/DMI等)，输出JSON结果供分析决策。当用户提到以下内容时触发：A股分析、技术指标、指标分析、股票分析、技术分析、均线、MACD、KDJ、RSI、布林带、BOLL、成交量分析、量能、选股。"
metadata: {"nanobot":{"triggers":["A股分析","技术指标","指标分析","股票分析","技术分析","均线分析","MACD","KDJ","RSI","布林带","BOLL","成交量分析","量能分析","选股","BigA","biga","大A"]}}
---

# A股技术指标分析

通过本地 Python 脚本获取 A 股行情数据（新浪/腾讯双源），计算 34 种技术指标，输出结构化 JSON。

数据源: 新浪财经(主) + 腾讯股票(备)，自动容灾切换，无需 API Key。

**【重要】向用户展示指标结果时，必须使用中文名称，不得直接输出英文缩写。**
例如：不要说 `MACD_DIF: 5.17`，要说 `MACD快线(DIF): 5.17`；不要说 `KDJ_K: 67.3`，要说 `KDJ的K值: 67.3`；不要说 `BBANDS_UPPER`，要说 `布林带上轨`。完整对照表见下方"指标速查表"。

## 快速使用

**脚本路径：** `nanobot/skills/biga-analysis/scripts/run.py`

**一步获取指标（推荐）：**

```python
import subprocess, json

result = subprocess.run(
    [
        "C:/Users/17140/anaconda3/envs/torch/python.exe",
        "nanobot/skills/biga-analysis/scripts/run.py",
        "sh600519",               # 股票代码
        "-i", "MACD,RSI,KDJ,BBANDS",  # 指定指标
        "-j"                      # JSON输出
    ],
    capture_output=True, text=True, encoding="utf-8"
)
data = json.loads(result.stdout)
# data["price"]      → 最新行情 (开/高/低/收/量)
# data["indicators"] → 指标计算结果
```

**常用命令：**

```bash
# 激活环境
conda activate torch

# 茅台日线，核心指标
python nanobot/skills/biga-analysis/scripts/run.py sh600519 -i MACD,RSI,KDJ,BBANDS -j

# 上证指数全部指标
python nanobot/skills/biga-analysis/scripts/run.py sh000001 -j

# 15分钟线
python nanobot/skills/biga-analysis/scripts/run.py sh600519 --freq 15m --count 60 -j

# 列出所有指标
python nanobot/skills/biga-analysis/scripts/run.py --list
```

## 证券代码格式

| 格式 | 示例 | 说明 |
|------|------|------|
| `sh` + 代码 | `sh600519` | 上证（通达信格式） |
| `sz` + 代码 | `sz000001` | 深证（通达信格式） |
| 代码 + `.XSHG` | `600519.XSHG` | 上证（聚宽格式） |
| 代码 + `.XSHE` | `000001.XSHE` | 深证（聚宽格式） |

常用指数: `sh000001`=上证指数, `sz399001`=深证成指, `sz399006`=创业板指

## K线周期

| 参数 | 周期 | 适用场景 |
|------|------|----------|
| `1d` | 日线（默认） | 中长线趋势分析 |
| `1w` | 周线 | 中期趋势判断 |
| `1M` | 月线 | 长期趋势 |
| `5m` `15m` `30m` `60m` | 分钟线 | 日内短线交易 |
| `1m` | 1分钟线 | 超短线/盘口分析 |

## 指标速查表

### 趋势类 — 判断方向和趋势强度

| 指标 | 说明 | 关键信号 |
|------|------|----------|
| **MACD** | 趋势动量 | DIF上穿DEA=金叉(买); 下穿=死叉(卖) |
| **DMI** | 趋向系统 | PDI>MDI且ADX>25=强上升趋势 |
| **ADX** | 趋势强度 | >25强趋势, <20无趋势 |
| **TRIX** | 三重平滑 | TRIX上穿0=买入, 下穿0=卖出 |
| **DMA** | 均线差 | DIF上穿DIFMA=买入 |
| **BBI** | 多空均线 | 价格>BBI=多头, <BBI=空头 |
| **SMA/EMA/WMA** | 移动平均 | 短期上穿长期=金叉 |

### 震荡类 — 判断超买超卖和反转点

| 指标 | 说明 | 关键信号 |
|------|------|----------|
| **KDJ** | 随机指标 | K>80超买, K<20超卖; J>100/J<0=极端 |
| **RSI** | 相对强弱 | >70超买, <30超卖 |
| **CCI** | 商品通道 | >100超买, <-100超卖 |
| **WILLR/WR** | 威廉指标 | >-20超买, <-80超卖 |
| **BIAS** | 乖离率 | 偏离越大越可能回归均值 |
| **PSY** | 心理线 | >75过热, <25过冷 |
| **MOM/MTM** | 动量 | >0上升趋势, <0下降趋势 |
| **ROC** | 变动率 | 衡量价格变化速度 |

### 波动率类 — 衡量市场波动和通道

| 指标 | 说明 | 关键信号 |
|------|------|----------|
| **BBANDS** | 布林带 | 触上轨=压力, 触下轨=支撑, 收窄=即将变盘 |
| **ATR** | 真实波幅 | 值越大波动越剧烈 |
| **TAQ** | 唐安奇通道 | 突破上轨=买, 跌破下轨=卖 |

### 量能类 — 通过成交量验证趋势

| 指标 | 说明 | 关键信号 |
|------|------|----------|
| **OBV** | 能量潮 | OBV上升+价格上升=趋势确认 |
| **MFI** | 资金流量 | >80超买, <20超卖 |
| **VR** | 量比 | >100多方主导, <100空方主导 |
| **AD/ADOSC** | 累积派发 | 与价格背离=趋势反转信号 |

### 情绪类

| 指标 | 说明 | 关键信号 |
|------|------|----------|
| **BRAR** | 情绪指标 | AR>100多方强, BR>100买意强 |

## 输出格式

JSON 输出包含两部分：

```json
{
  "price": {
    "code": "sh600519",
    "frequency": "1d",
    "last_time": "2026-04-08",
    "open": 1460.0, "close": 1465.02,
    "high": 1469.08, "low": 1452.13,
    "volume": 3383610.0,
    "count": 120
  },
  "indicators": {
    "MACD_DIF": 5.17, "MACD_DEA": 1.08, "MACD_MACD_HIST": 8.18,
    "RSI": 48.93,
    "KDJ_K": 67.31, "KDJ_D": 57.95, "KDJ_J": 86.02,
    "BBANDS_UPPER": 1490.58, "BBANDS_MID": 1435.74, "BBANDS_LOWER": 1380.89
  }
}
```

多返回值指标的字段命名规则: `指标名_子名`（如 `MACD_DIF`, `KDJ_K`, `BBANDS_UPPER`）

## 分析建议模板

当用户请求分析某只股票时，按以下步骤操作：

### 第1步：获取数据 + 核心指标

```python
result = analyze('sh600519', indicators=['MACD', 'RSI', 'KDJ', 'BBANDS', 'DMI', 'OBV', 'ATR'])
```

### 第2步：解读指标组合

综合多个指标判断，避免单一指标误判：

1. **趋势方向**: MACD(DIF与DEA关系) + DMI(PDI vs MDI)
2. **买卖时机**: KDJ(超买超卖) + RSI(强弱)
3. **支撑压力**: BBANDS(布林通道位置)
4. **趋势确认**: OBV(量价配合) + ATR(波动程度)

### 第3步：给出结论

- 明确多空判断和依据
- 标注关键支撑/压力位
- 提示风险因素
- **声明: 仅供参考，不构成投资建议**

## 详细参考文档

当需要更深入的信息时，**必须用 `read_file` 读取以下文档**：

**指标详解（公式、参数、信号、组合策略）：**
```
read_file(path="nanobot/skills/biga-analysis/references/indicators-guide.md")
```

**LLM调用指南（场景决策树、代码模板、回复模板）：**
```
read_file(path="nanobot/skills/biga-analysis/references/quick-start.md")
```

何时读取哪个文档：
- 用户问"XX指标怎么看" / 需要解释指标含义 → 读 `indicators-guide.md`
- 用户问"分析XX股票" / 需要组合调用多个指标 → 读 `quick-start.md`
- 用户只是查个数值 → 不需要读，直接调用脚本即可

## 注意事项

- 数据源为新浪/腾讯免费接口，非交易时间返回最近交易日数据
- 分钟线数据量有限（腾讯约提供近几个交易日）
- 建议 count ≥ 120 以保证长周期指标（如MACD 26期、BOLL 20期）精度
- 需要在 `conda activate torch` 环境下运行（base 环境 numpy 版本不兼容）
- A股交易时间: 工作日 9:30-11:30, 13:00-15:00（北京时间）

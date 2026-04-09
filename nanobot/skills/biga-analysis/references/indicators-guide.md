# 技术指标详细指南

本文档包含**脚本调用方法**以及每个指标的计算公式、参数说明、信号解读、实战组合用法。

---

## 零、脚本调用方法

所有指标通过 `run.py` 脚本计算，脚本位于：
```
nanobot/skills/biga-analysis/scripts/run.py
```

### 调用方式一：exec 执行（推荐，LLM 最常用）

```python
import subprocess, json

result = subprocess.run(
    [
        "C:/Users/17140/anaconda3/envs/torch/python.exe",
        "nanobot/skills/biga-analysis/scripts/run.py",
        "sh600519",          # 股票代码
        "-i", "MACD,RSI,KDJ,BBANDS",  # 指定指标，逗号分隔
        "-j"                 # JSON输出
    ],
    capture_output=True, text=True, encoding="utf-8"
)
data = json.loads(result.stdout)
price = data["price"]        # 行情快照
indicators = data["indicators"]  # 指标结果
```

### 调用方式二：命令行直接运行

```bash
# 激活环境（必须）
conda activate torch

# 茅台日线，指定指标，JSON输出
python nanobot/skills/biga-analysis/scripts/run.py sh600519 -i MACD,RSI,KDJ,BBANDS -j

# 全部指标
python nanobot/skills/biga-analysis/scripts/run.py sh000001 -j

# 15分钟线，60根K线
python nanobot/skills/biga-analysis/scripts/run.py sh600519 --freq 15m --count 60 -j

# 列出所有可用指标名
python nanobot/skills/biga-analysis/scripts/run.py --list
```

### 参数说明

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| 第一位置参数 | — | 证券代码（必填） | `sh600519` |
| `--freq` | `-f` | K线周期 | `1d` `1w` `1M` `5m` `15m` `30m` `60m` |
| `--count` | `-c` | K线数量，默认120 | `--count 60` |
| `--indicators` | `-i` | 指定指标，逗号分隔 | `-i MACD,RSI,KDJ` |
| `--json` | `-j` | JSON格式输出 | `-j` |
| `--list` | `-l` | 列出所有指标名 | `--list` |

### 输出格式

```json
{
  "price": {
    "code": "sh600519",
    "frequency": "1d",
    "last_time": "2026-04-08 00:00:00",
    "open": 1460.0, "close": 1465.02,
    "high": 1469.08, "low": 1452.13,
    "volume": 3383610.0, "count": 120
  },
  "indicators": {
    "MACD_DIF": 5.1713,
    "MACD_DEA": 1.0798,
    "MACD_MACD_HIST": 8.183,
    "RSI": 48.934,
    "KDJ_K": 67.3073, "KDJ_D": 57.9519, "KDJ_J": 86.0183,
    "BBANDS_UPPER": 1490.58, "BBANDS_MID": 1435.74, "BBANDS_LOWER": 1380.89
  }
}
```

多返回值指标的字段命名：`指标名_子名`，如 `MACD_DIF`、`KDJ_K`、`BBANDS_UPPER`。

### 全部可用指标名

趋势类: `SMA` `EMA` `WMA` `MACD` `ADX` `DMI` `DMA` `TRIX` `BBI` `LINEARREG`

震荡类: `RSI` `KDJ` `STOCH` `CCI` `WILLR` `WR` `MOM` `MTM` `ROC` `BIAS` `PSY` `DPO`

波动率类: `BBANDS` `ATR` `NATR` `TAQ` `EMV` `STDDEV`

量能类: `OBV` `AD` `ADOSC` `MFI` `VR`

情绪类: `BRAR`

### 环境要求

- Python：`C:/Users/17140/anaconda3/envs/torch/python.exe`
- 依赖：pandas、numpy、requests（torch 环境已内置）
- 网络：需访问新浪/腾讯财经 API（国内网络）
- 数据：非交易时间返回最近交易日数据

---

## 一、趋势类指标

### MACD — 指数平滑异同移动平均线

**计算公式：**
```
DIF  = EMA(CLOSE, 12) - EMA(CLOSE, 26)
DEA  = EMA(DIF, 9)
MACD柱 = (DIF - DEA) × 2
```

**参数：** `fastperiod=12, slowperiod=26, signalperiod=9`

**信号解读：**
- **金叉**：DIF 从下向上穿越 DEA → 买入信号
- **死叉**：DIF 从上向下穿越 DEA → 卖出信号
- **零轴上方金叉**：强势买入（趋势确认）
- **零轴下方死叉**：强势卖出
- **顶背离**：价格新高但 DIF 未新高 → 见顶信号
- **底背离**：价格新低但 DIF 未新低 → 见底信号
- **MACD柱由绿变红**：空转多
- **MACD柱由红变绿**：多转空

**调用：**
```python
result = analyze('sh600519', indicators=['MACD'])
# 返回: MACD_DIF, MACD_DEA, MACD_MACD_HIST
```

---

### DMI — 动向指标 (Directional Movement Index)

**计算公式：**
```
TR  = SUM(MAX(HIGH-LOW, |HIGH-REF(CLOSE,1)|, |LOW-REF(CLOSE,1)|), M1)
DMP = SUM(正向动量, M1)   # HIGH-REF(HIGH,1) > 0 且 > LD 时取值
DMM = SUM(负向动量, M1)   # REF(LOW,1)-LOW > 0 且 > HD 时取值
PDI = DMP × 100 / TR      # 正向指标
MDI = DMM × 100 / TR      # 负向指标
ADX = MA(|MDI-PDI|/(PDI+MDI)×100, M2)   # 趋势强度
ADXR = (ADX + REF(ADX, M2)) / 2          # 平滑ADX
```

**参数：** `m1=14, m2=6`

**信号解读：**
- **PDI > MDI**：上升趋势占优
- **MDI > PDI**：下降趋势占优
- **ADX > 25**：趋势明确（值越大趋势越强）
- **ADX < 20**：盘整，不宜趋势交易
- **PDI上穿MDI + ADX>25**：强势买入
- **MDI上穿PDI + ADX>25**：强势卖出

**调用：**
```python
result = analyze('sh600519', indicators=['DMI'])
# 返回: DMI_PDI, DMI_MDI, DMI_ADX, DMI_ADXR
```

---

### ADX — 平均趋向指标

DMI 的简化版，只返回趋势强度值。

**参数：** `timeperiod=14`

**信号：** >25 强趋势，>50 极强趋势，<20 无趋势/盘整

---

### TRIX — 三重指数平滑

**计算公式：**
```
TR   = EMA(EMA(EMA(CLOSE, M1), M1), M1)
TRIX = (TR - REF(TR, 1)) / REF(TR, 1) × 100
TRMA = MA(TRIX, M2)
```

**参数：** `m1=12, m2=20`

**信号：** TRIX上穿TRMA=买入，下穿=卖出。适合过滤短期波动，捕捉中期趋势。

---

### DMA — 平行线差指标

**计算公式：**
```
DIF   = MA(CLOSE, N1) - MA(CLOSE, N2)
DIFMA = MA(DIF, M)
```

**参数：** `n1=10, n2=50, m=10`

**信号：** DIF上穿DIFMA=买入，下穿=卖出

---

### BBI — 多空指标

**公式：** `(MA(C,3) + MA(C,6) + MA(C,12) + MA(C,20)) / 4`

**信号：** 价格站上BBI=多头，跌破BBI=空头

---

### SMA / EMA / WMA — 移动平均线

| 类型 | 特点 | 默认周期 |
|------|------|----------|
| SMA | 等权重，反应较慢 | 14 |
| EMA | 近期权重大，反应灵敏 | 12 |
| WMA | 线性加权，介于两者之间 | 10 |

**常用组合：** MA5/MA10/MA20/MA60
- 短期均线上穿长期均线 = 金叉
- 均线多头排列（5>10>20>60）= 强势

---

## 二、震荡类指标

### KDJ — 随机指标

**计算公式：**
```
RSV = (CLOSE - LLV(LOW, 9)) / (HHV(HIGH, 9) - LLV(LOW, 9)) × 100
K   = EMA(RSV, 5)    # M1×2-1
D   = EMA(K, 5)      # M2×2-1
J   = 3K - 2D
```

**参数：** `n=9, m1=3, m2=3`

**信号解读：**
- **K>80, D>80**：超买区，注意回调
- **K<20, D<20**：超卖区，注意反弹
- **J>100**：极度超买（短线卖出信号）
- **J<0**：极度超卖（短线买入信号）
- **K上穿D（金叉）**：买入信号
- **K下穿D（死叉）**：卖出信号
- **低位金叉（K<20时）**：强买入

---

### RSI — 相对强弱指数

**计算公式：**
```
涨幅均值 = MA(MAX(CLOSE-REF(CLOSE,1), 0), N)
跌幅均值 = MA(ABS(CLOSE-REF(CLOSE,1)), N) - 涨幅均值
RSI = 涨幅均值 / (涨幅均值 + 跌幅均值) × 100
```

**参数：** `timeperiod=14`（也常用6、24）

**信号：**
- **>70**：超买，可能回调
- **<30**：超卖，可能反弹
- **>80**：严重超买
- **<20**：严重超卖
- **50附近**：多空平衡

---

### CCI — 商品通道指数

**公式：** `(TP - MA(TP, N)) / (0.015 × AVEDEV(TP, N))`，其中 TP=(H+L+C)/3

**参数：** `timeperiod=14`

**信号：** >100 超买，<-100 超卖，CCI从-100下方上穿-100=买入信号

---

### WILLR / WR — 威廉指标

**WILLR 公式：** `-100 × (HHV(H,N) - C) / (HHV(H,N) - LLV(L,N))`，范围 -100~0

**WR 公式（通达信版）：** 同上但不取负，范围 0~100

**信号：** WR<20(WILLR>-20) 超买，WR>80(WILLR<-80) 超卖

---

### BIAS — 乖离率

**公式：** `(CLOSE - MA(CLOSE, N)) / MA(CLOSE, N) × 100`

**参数：** `l1=6, l2=12, l3=24` 返回三条乖离线

**信号：** 正乖离过大=可能回调，负乖离过大=可能反弹。具体阈值因个股而异。

---

### PSY — 心理线

**公式：** `近N日上涨天数 / N × 100`

**参数：** `n=12, m=6`

**信号：** >75 市场过热，<25 市场过冷

---

### MOM / MTM — 动量指标

**MOM公式：** `CLOSE - REF(CLOSE, N)`
**MTM公式：** 同上，额外返回 MA(MTM, M)

**信号：** >0 上升趋势，<0 下降趋势，穿越零线=趋势转换

---

### ROC — 变动率

**公式：** `(CLOSE - REF(CLOSE, N)) / REF(CLOSE, N) × 100`

**信号：** 本质是动量的百分比版本，便于不同价位股票对比

---

## 三、波动率类指标

### BBANDS — 布林带

**计算公式：**
```
MID   = MA(CLOSE, 20)
UPPER = MID + STD(CLOSE, 20) × 2
LOWER = MID - STD(CLOSE, 20) × 2
```

**参数：** `timeperiod=20, nbdevup=2, nbdevdn=2`

**信号解读：**
- **价格触及上轨**：遇阻回落概率大
- **价格触及下轨**：获得支撑概率大
- **布林带收窄**：即将出现大幅波动（变盘信号）
- **布林带张口向上**：上升趋势加速
- **价格沿上轨运行**：强势上涨
- **价格沿下轨运行**：弱势下跌

---

### ATR — 平均真实波幅

**公式：** `MA(MAX(H-L, |H-REF(C,1)|, |L-REF(C,1)|), N)`

**参数：** `timeperiod=14`

**用途：** 不判断方向，只衡量波动大小。常用于：
- 设置止损位：当前价 ± 2×ATR
- 判断波动变化：ATR放大=波动加剧

**NATR = ATR/CLOSE × 100**，归一化版本，可跨股票比较。

---

### TAQ — 唐安奇通道

**公式：** `UP=HHV(H,N), DOWN=LLV(L,N), MID=(UP+DOWN)/2`

**参数：** `n=20`

**信号：** 突破上轨=做多，跌破下轨=做空。经典趋势跟踪策略，"大道至简"。

---

### EMV — 简易波动指标

衡量价格变动的"容易程度"。EMV大=价格容易上涨，EMV小=上涨阻力大。

**信号：** EMV上穿0=买入，下穿0=卖出

---

## 四、量能类指标

### OBV — 能量潮

**公式：** 今日收盘>昨日 → 加今日成交量；反之减去

**信号：**
- OBV上升 + 价格上升 = 量价配合，趋势健康
- OBV下降 + 价格上升 = 量价背离，上涨乏力
- OBV大幅上升 + 价格横盘 = 主力吸筹

---

### MFI — 资金流量指标

**类似RSI但加入了成交量因素。**

**参数：** `timeperiod=14`

**信号：** >80 资金过度流入（超买），<20 资金过度流出（超卖）

---

### VR — 成交量比率

**公式：** 上涨日成交量之和 / 下跌日成交量之和 × 100

**信号：** >100 多方量能占优，<100 空方量能占优

---

### AD / ADOSC — 累积派发线

**AD公式：** `CLV × Volume` 的累计和，其中 CLV=((C-L)-(H-C))/(H-L)

**ADOSC = EMA(AD, fast) - EMA(AD, slow)**

**信号：** AD与价格背离=趋势即将反转

---

## 五、情绪类指标

### BRAR — 多空情绪

**AR公式：** `SUM(H-O, 26) / SUM(O-L, 26) × 100`（人气指标）
**BR公式：** `SUM(MAX(0,H-REF(C,1)), 26) / SUM(MAX(0,REF(C,1)-L), 26) × 100`（买卖意愿）

**信号：**
- AR>100: 多方活跃
- BR>100: 买入意愿强
- AR、BR同时极高: 过热，可能见顶

---

## 六、指标组合策略

### 趋势确认组合
```
MACD + DMI + OBV
```
MACD判方向 → DMI确认趋势强度 → OBV验证量价配合

### 超买超卖组合
```
KDJ + RSI + BBANDS
```
KDJ看短期极端 → RSI确认强弱 → BBANDS看价格在通道中的位置

### 短线交易组合
```
KDJ + MACD + ATR
```
KDJ找买卖点 → MACD确认趋势 → ATR设止损

### 完整分析建议
```python
# 一次获取全面分析所需的所有指标
result = analyze('sh600519', indicators=[
    'MACD', 'DMI', 'RSI', 'KDJ', 'BBANDS', 'ATR', 'OBV', 'MFI', 'BRAR'
])
```

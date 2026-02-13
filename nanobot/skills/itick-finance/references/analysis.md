# 技术分析与基本面分析指南

获取 K 线数据后，通过 exec 运行 Python 脚本计算技术指标。以下所有代码仅使用 Python 标准库。

## 技术指标

### 1. 移动平均线 (MA)

```python
def calc_ma(closes, period):
    """计算简单移动平均线"""
    return [sum(closes[i-period+1:i+1])/period for i in range(period-1, len(closes))]

# 常用周期: MA5, MA10, MA20, MA60, MA120, MA250
# 信号:
#   金叉: 短期MA上穿长期MA -> 买入信号
#   死叉: 短期MA下穿长期MA -> 卖出信号
```

### 2. 指数移动平均线 (EMA)

```python
def calc_ema(closes, period):
    """计算指数移动平均线"""
    k = 2 / (period + 1)
    ema = [closes[0]]
    for i in range(1, len(closes)):
        ema.append(closes[i] * k + ema[-1] * (1 - k))
    return ema
```

### 3. MACD

```python
def calc_macd(closes, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    dif = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    dea = calc_ema(dif, signal)
    macd = [2 * (dif[i] - dea[i]) for i in range(len(closes))]
    return dif, dea, macd

# 信号:
#   DIF上穿DEA(金叉) -> 买入
#   DIF下穿DEA(死叉) -> 卖出
#   MACD柱由负转正 -> 多头增强
#   MACD柱由正转负 -> 空头增强
#   底背离(价格新低但MACD未新低) -> 反转买入信号
#   顶背离(价格新高但MACD未新高) -> 反转卖出信号
```

### 4. RSI (相对强弱指数)

```python
def calc_rsi(closes, period=14):
    """计算RSI指标"""
    rsi_values = []
    changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]

    gains = [max(0, c) for c in changes[:period]]
    losses = [max(0, -c) for c in changes[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        rsi_values.append(100)
    else:
        rsi_values.append(100 - 100 / (1 + avg_gain / avg_loss))

    for i in range(period, len(changes)):
        gain = max(0, changes[i])
        loss = max(0, -changes[i])
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rsi_values.append(100 - 100 / (1 + avg_gain / avg_loss))

    return rsi_values

# 常用周期: RSI6, RSI12, RSI24
# 信号:
#   RSI > 80 -> 超买区域，可能回调
#   RSI < 20 -> 超卖区域，可能反弹
#   RSI 50 为多空分界线
```

### 5. 布林带 (Bollinger Bands)

```python
import math

def calc_bollinger(closes, period=20, num_std=2):
    """计算布林带"""
    upper, middle, lower = [], [], []
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        ma = sum(window) / period
        variance = sum((x - ma) ** 2 for x in window) / period
        std = math.sqrt(variance)
        middle.append(ma)
        upper.append(ma + num_std * std)
        lower.append(ma - num_std * std)
    return upper, middle, lower

# 信号:
#   价格触及上轨 -> 超买，可能回落
#   价格触及下轨 -> 超卖，可能反弹
#   带宽收窄 -> 即将变盘
#   带宽扩大 -> 趋势加速
```

### 6. KDJ 指标

```python
def calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    k_values, d_values, j_values = [], [], []
    k, d = 50, 50  # 初始值

    for i in range(n - 1, len(closes)):
        hn = max(highs[i - n + 1:i + 1])
        ln = min(lows[i - n + 1:i + 1])
        if hn == ln:
            rsv = 50
        else:
            rsv = (closes[i] - ln) / (hn - ln) * 100
        k = (m1 - 1) / m1 * k + 1 / m1 * rsv
        d = (m2 - 1) / m2 * d + 1 / m2 * k
        j = 3 * k - 2 * d
        k_values.append(round(k, 2))
        d_values.append(round(d, 2))
        j_values.append(round(j, 2))

    return k_values, d_values, j_values

# 信号:
#   K上穿D(金叉) -> 买入
#   K下穿D(死叉) -> 卖出
#   J > 100 -> 超买
#   J < 0 -> 超卖
```

### 7. 成交量分析

```python
def analyze_volume(closes, volumes, period=5):
    """成交量趋势分析"""
    avg_vol = sum(volumes[-period:]) / period
    latest_vol = volumes[-1]
    price_change = closes[-1] - closes[-2]

    ratio = latest_vol / avg_vol if avg_vol > 0 else 1

    if ratio > 2 and price_change > 0:
        return "放量上涨 - 强势信号"
    elif ratio > 2 and price_change < 0:
        return "放量下跌 - 弱势信号"
    elif ratio < 0.5 and price_change > 0:
        return "缩量上涨 - 上涨动力不足"
    elif ratio < 0.5 and price_change < 0:
        return "缩量下跌 - 下跌趋缓"
    else:
        return "量价正常"
```

---

## 基本面分析

通过 /stock/info 接口获取财务数据后进行分析:

### 市盈率 (PE) 分析

| PE 范围 | 估值参考 |
|---------|---------|
| < 0 | 亏损 |
| 0-15 | 低估值 |
| 15-25 | 合理估值 |
| 25-40 | 较高估值 |
| > 40 | 高估值 |

注意: PE 需结合行业特征判断。科技/成长股通常 PE 较高，银行/周期股 PE 较低。

### 市值分析

| 市值 (人民币) | 分类 |
|--------------|------|
| > 1000亿 | 大盘股 |
| 100-1000亿 | 中盘股 |
| < 100亿 | 小盘股 |

---

## 综合分析模板

当用户要求分析某只股票时，建议按以下步骤:

1. **获取基本信息** - 调用 /stock/info 了解公司概况
2. **获取实时行情** - 调用 /stock/quote 查看当前价格和涨跌
3. **获取日K线** - 调用 /stock/kline (kType=8, limit=60) 获取近60日数据
4. **计算技术指标** - 用 exec 运行 Python 计算 MA/RSI/MACD
5. **查看盘口** - 调用 /stock/depth 查看买卖力量对比
6. **综合判断** - 结合技术面和基本面给出分析结论

输出格式建议:
```
## {股票名} ({代码}) 分析报告

### 基本面
- 行业: xxx
- 市盈率: xxx
- 总市值: xxx

### 当前行情
- 最新价: xxx | 涨跌: xxx (xxx%)
- 成交量: xxx | 成交额: xxx

### 技术指标
- MA5/10/20: xxx / xxx / xxx
- RSI(14): xxx
- MACD: DIF=xxx DEA=xxx

### 综合判断
xxx
```

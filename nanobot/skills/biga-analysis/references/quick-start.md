# LLM 调用模式与常见场景

本文档面向 LLM agent，说明如何根据用户意图选择正确的调用方式。

**脚本路径：** `nanobot/skills/biga-analysis/scripts/run.py`
**Python路径：** `C:/Users/17140/anaconda3/envs/torch/python.exe`

---

## 调用决策树

```
用户提问
  │
  ├─ "XX股票怎么样" / "分析一下XX"
  │   → 完整分析模式（核心指标组合）
  │
  ├─ "XX的MACD/RSI/KDJ是多少"
  │   → 指定指标模式（只算需要的）
  │
  ├─ "XX是不是超买了" / "该不该买"
  │   → 超买超卖判断模式
  │
  ├─ "XX趋势如何" / "是涨还是跌"
  │   → 趋势判断模式
  │
  ├─ "帮我看看这几只股票"
  │   → 多股票对比模式（逐个调用）
  │
  └─ "XX的分钟线/短线分析"
      → 短线模式（改freq参数）
```

---

## 场景1: 完整分析

用户说: "分析一下茅台"

```python
import subprocess, json

r = subprocess.run(
    [
        "C:/Users/17140/anaconda3/envs/torch/python.exe",
        "nanobot/skills/biga-analysis/scripts/run.py",
        "sh600519",
        "-i", "MACD,RSI,KDJ,BBANDS,DMI,ATR,OBV,MFI,BRAR",
        "-j"
    ],
    capture_output=True, text=True, encoding="utf-8"
)
data = json.loads(r.stdout)
```

**回复模板：**
```
## 贵州茅台 (600519) 技术面分析

**行情快照：** 收盘 {close}，涨跌幅根据开盘价计算

**趋势判断：**
- MACD: DIF={DIF}, DEA={DEA}，{金叉/死叉}，{零轴上方/下方} → {多头/空头}
- DMI: PDI={PDI}, MDI={MDI}, ADX={ADX} → {趋势方向和强度}

**买卖信号：**
- KDJ: K={K}, D={D}, J={J} → {超买/超卖/中性}
- RSI: {RSI} → {超买/超卖/中性}

**通道位置：**
- 布林带: 上轨{UPPER}, 中轨{MID}, 下轨{LOWER}
- 当前价在{上轨附近/中轨附近/下轨附近} → {压力/中性/支撑}

**量能验证：**
- OBV: {上升/下降} → {量价配合/背离}
- MFI: {MFI} → {资金流入/流出}

**综合判断：** {偏多/偏空/中性观望}

⚠️ 以上分析仅供参考，不构成投资建议。
```

---

## 场景2: 指定指标查询

用户说: "茅台的MACD是多少"

```python
r = subprocess.run(
    [
        "C:/Users/17140/anaconda3/envs/torch/python.exe",
        "nanobot/skills/biga-analysis/scripts/run.py",
        "sh600519", "-i", "MACD", "-j"
    ],
    capture_output=True, text=True, encoding="utf-8"
)
data = json.loads(r.stdout)
```

直接返回指标值 + 简要解读即可。

---

## 场景3: 超买超卖判断

用户说: "平安银行是不是超买了"

```python
r = subprocess.run(
    [
        "C:/Users/17140/anaconda3/envs/torch/python.exe",
        "nanobot/skills/biga-analysis/scripts/run.py",
        "sz000001", "-i", "RSI,KDJ,CCI,MFI,WILLR,BBANDS", "-j"
    ],
    capture_output=True, text=True, encoding="utf-8"
)
data = json.loads(r.stdout)
ind = data["indicators"]
```

**判断逻辑：**
```
超买信号计数 = 0
if RSI > 70:        超买信号计数 += 1
if KDJ_K > 80:      超买信号计数 += 1
if CCI > 100:       超买信号计数 += 1
if MFI > 80:        超买信号计数 += 1
if WILLR > -20:     超买信号计数 += 1

if 超买信号计数 >= 3:  "多指标共振，超买信号较强"
elif 超买信号计数 >= 2: "有一定超买迹象"
else:                    "暂未出现明显超买"
```

---

## 场景4: 趋势判断

用户说: "上证指数趋势怎么样"

```python
r = subprocess.run(
    [
        "C:/Users/17140/anaconda3/envs/torch/python.exe",
        "nanobot/skills/biga-analysis/scripts/run.py",
        "sh000001", "-i", "MACD,DMI,ADX,TRIX,BBI,EMA", "-j"
    ],
    capture_output=True, text=True, encoding="utf-8"
)
data = json.loads(r.stdout)
```

**判断逻辑：**
- MACD_DIF > MACD_DEA → 多头
- DMI_PDI > DMI_MDI → 上升
- ADX > 25 → 趋势明确
- CLOSE > BBI → 多方控制

---

## 场景5: 短线/日内分析

用户说: "茅台15分钟线怎么看"

```python
r = subprocess.run(
    [
        "C:/Users/17140/anaconda3/envs/torch/python.exe",
        "nanobot/skills/biga-analysis/scripts/run.py",
        "sh600519", "--freq", "15m", "--count", "60",
        "-i", "MACD,KDJ,RSI,BBANDS", "-j"
    ],
    capture_output=True, text=True, encoding="utf-8"
)
data = json.loads(r.stdout)
```

短线分析重点关注 KDJ（反应最快）+ MACD（确认） + BBANDS（支撑压力位）。

---

## 场景6: 多股票对比

用户说: "比较一下茅台和五粮液"

```python
import subprocess, json

PYTHON = "C:/Users/17140/anaconda3/envs/torch/python.exe"
SCRIPT = "nanobot/skills/biga-analysis/scripts/run.py"

stocks = [("sh600519", "贵州茅台"), ("sz000858", "五粮液")]
results = {}
for code, name in stocks:
    r = subprocess.run(
        [PYTHON, SCRIPT, code, "-i", "MACD,RSI,KDJ,ATR", "-j"],
        capture_output=True, text=True, encoding="utf-8"
    )
    results[name] = json.loads(r.stdout)
```

---

## 常用股票代码速查

| 代码 | 名称 | 代码 | 名称 |
|------|------|------|------|
| sh000001 | 上证指数 | sz399001 | 深证成指 |
| sz399006 | 创业板指 | sh000300 | 沪深300 |
| sh600519 | 贵州茅台 | sz000858 | 五粮液 |
| sh601318 | 中国平安 | sz000001 | 平安银行 |
| sh600036 | 招商银行 | sz000333 | 美的集团 |
| sh601899 | 紫金矿业 | sz300750 | 宁德时代 |

---

## 错误处理

```python
r = subprocess.run([...], capture_output=True, text=True, encoding="utf-8")
if r.returncode != 0:
    # 网络问题或代码格式错误
    print("数据获取失败:", r.stderr)
    # 告诉用户"数据获取失败，请检查网络连接或股票代码"

data = json.loads(r.stdout)
if "error" in data:
    # 无法获取该股票数据
    print(data["error"])
```

---

## 环境要求

- Python路径: `C:/Users/17140/anaconda3/envs/torch/python.exe`
- 依赖: pandas, numpy, requests（torch 环境已内置）
- 网络: 需要访问新浪/腾讯财经 API（国内网络）
- A股交易时间: 工作日 9:30-11:30, 13:00-15:00（北京时间）

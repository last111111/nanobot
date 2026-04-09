# FINANCE_CLAUDE.md — Ashare-main & Finance-master 项目分析

## 一、项目总览

本仓库包含两个金融量化分析项目：

| 项目 | 定位 | 市场 | 语言 |
|------|------|------|------|
| **Ashare-main** | 极简 A 股实时行情 API + 技术指标库 | 中国 A 股 | Python |
| **Finance-master** | 150+ 独立脚本的量化金融工具集 | 美股（S&P500/NASDAQ/NYSE） | Python |

---

## 二、Ashare-main 详解

### 2.1 作用

提供**中国 A 股**实时和历史行情数据的轻量 API 封装，附带完整的通达信/同花顺技术指标计算库（MyTT）。适用于量化研究、回测、自动化交易系统。

### 2.2 核心文件

| 文件 | 作用 |
|------|------|
| `Ashare.py` | 行情数据 API（双源自动切换） |
| `MyTT.py` | 技术指标计算库（30+ 指标） |
| `Demo1.py` | 基础用法演示（数据获取） |
| `Demo2.py` | 进阶演示（指标计算 + matplotlib 可视化） |

### 2.3 数据源架构（双内核容灾）

```
get_price(code, frequency, count, end_date)
    │
    ├─ 日/周/月线 (1d/1w/1M)
    │   ├─ 主源: 新浪财经 (get_price_sina)
    │   └─ 备源: 腾讯股票 (get_price_day_tx)
    │
    └─ 分钟线 (1m/5m/15m/30m/60m)
        ├─ 1m: 仅腾讯 (get_price_min_tx)
        └─ 其他: 主源新浪，备源腾讯
```

**API 地址：**
- 新浪：`money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData`
- 腾讯：`web.ifzq.gtimg.cn/appstock/app/fqkline/get`（日线）、`ifzq.gtimg.cn/appstock/app/kline/mkline`（分钟线）

### 2.4 支持的证券代码格式

| 格式 | 示例 | 来源 |
|------|------|------|
| `sh`/`sz` 前缀 | `sh600519`, `sz399006` | 通达信格式 |
| `.XSHG`/`.XSHE` 后缀 | `600519.XSHG`, `399006.XSHE` | 聚宽格式 |

### 2.5 支持的时间周期

| 参数 | 周期 | 数据源 |
|------|------|--------|
| `1d` | 日线 | 新浪(主) / 腾讯(备) |
| `1w` | 周线 | 新浪(主) / 腾讯(备) |
| `1M` | 月线 | 新浪(主) / 腾讯(备) |
| `1m` | 1分钟 | 仅腾讯 |
| `5m` `15m` `30m` `60m` | 分钟线 | 新浪(主) / 腾讯(备) |

### 2.6 核心函数

#### `get_price(code, end_date='', count=10, frequency='1d', fields=[])`
主入口函数。自动规范化证券代码、按频率路由到对应数据源、异常时自动切换备源。返回 pandas DataFrame（datetime 索引，OHLCV 列）。

#### `get_price_sina(code, end_date, count, frequency)`
新浪数据源。日/周/月线通过内部映射转为分钟数（`1d→240m`, `1w→1200m`, `1M→7200m`）。历史数据请求时自动计算需要多取的天数以覆盖交易日缺口，按 end_date 截断返回。

#### `get_price_day_tx(code, end_date, count, frequency)`
腾讯日/周/月线数据源。使用前复权（qfq）价格。end_date 为当天时自动省略参数优化请求。

#### `get_price_min_tx(code, end_date, count, frequency)`
腾讯分钟线数据源。会用实时报价（`qt[code][3]`）更新最后一根 K 线的收盘价。

### 2.7 MyTT 技术指标库

分三层架构实现：

#### 第 0 层：基础运算函数

| 函数 | 作用 |
|------|------|
| `MA(S, N)` | N 期简单移动平均 |
| `EMA(S, N)` | 指数移动平均（pandas ewm） |
| `SMA(S, N, M)` | 中国式加权移动平均（alpha=M/N） |
| `REF(S, N)` | 序列前移 N 期 |
| `HHV(S, N)` / `LLV(S, N)` | N 期最高/最低值 |
| `STD(S, N)` | N 期标准差 |
| `SUM(S, N)` | N 期滚动求和 |
| `SLOPE(S, N)` | 线性回归斜率 |
| `IF(S_BOOL, S_TRUE, S_FALSE)` | 条件选择 |
| `CROSS(S1, S2)` | 金叉检测（S1 上穿 S2） |

#### 第 1 层：应用函数

| 函数 | 作用 |
|------|------|
| `COUNT(S_BOOL, N)` | N 期内 True 计数 |
| `EVERY(S_BOOL, N)` | N 期内全部为 True |
| `EXIST(S_BOOL, N)` | N 期内存在 True |
| `BARSLAST(S_BOOL)` | 距上次条件成立的 K 线数 |
| `FORCAST(S, N)` | 线性回归预测下一值 |
| `CROSS(S1, S2)` | 交叉检测 |

#### 第 2 层：技术指标（30+ 个）

**趋势类：**
- `MACD(CLOSE, 12, 26, 9)` → DIF/DEA/MACD柱
- `DMI(CLOSE, HIGH, LOW, 14, 6)` → PDI/MDI/ADX/ADXR
- `TRIX(CLOSE, 12, 20)` → 三重指数平滑
- `DMA(CLOSE, 10, 50, 10)` → 平行线差指标
- `BBI(CLOSE, 3, 6, 12, 20)` → 多空指标

**震荡类：**
- `KDJ(CLOSE, HIGH, LOW, 9, 3, 3)` → K/D/J
- `RSI(CLOSE, 24)` → 相对强弱指数
- `WR(CLOSE, HIGH, LOW, 10, 6)` → 威廉指标
- `CCI(CLOSE, HIGH, LOW, 14)` → 商品通道指数
- `ROC(CLOSE, 12, 6)` → 变动率
- `MTM(CLOSE, 12, 6)` → 动量指标

**波动类：**
- `BOLL(CLOSE, 20, 2)` → 布林带（上轨/中轨/下轨）
- `ATR(CLOSE, HIGH, LOW, 20)` → 平均真实波幅
- `TAQ(HIGH, LOW, N)` → 唐安奇通道

**情绪/量能类：**
- `BIAS(CLOSE, 6, 12, 24)` → 乖离率
- `PSY(CLOSE, 12, 6)` → 心理线
- `BRAR(OPEN, CLOSE, HIGH, LOW, 26)` → 情绪指标
- `VR(CLOSE, VOL, 26)` → 成交量比率
- `EMV(HIGH, LOW, VOL, 14, 9)` → 简易波动指标

---

## 三、Finance-master 详解

### 3.1 作用

美股量化金融工具集，涵盖**选股筛选、机器学习预测、策略回测、个股分析、数据采集、技术指标可视化**六大模块，共 150+ 独立可执行脚本。

### 3.2 项目结构

```
Finance-master/
├── tickers.py              # 股票代码获取（S&P500/NASDAQ/NYSE/DOW/AMEX）
├── ta_functions.py         # 技术指标计算库（50+ 指标）
├── find_stocks/            # 选股筛选器
├── machine_learning/       # 机器学习预测模型
├── portfolio_strategies/   # 投资组合策略 & 回测
├── stock_analysis/         # 个股分析工具
├── stock_data/             # 数据采集工具
└── technical_indicators/   # 70+ 技术指标可视化
```

### 3.3 公共模块

#### `tickers.py` — 股票代码获取

| 函数 | 数据源 | 返回 |
|------|--------|------|
| `tickers_sp500()` | Wikipedia 爬取 | ~500 只 S&P 500 成分股 |
| `tickers_nasdaq()` | nasdaqtrader.com | ~5000 只 NASDAQ 股票 |
| `tickers_nyse()` | nasdaqtrader.com (Exchange='N') | ~2500 只 NYSE 股票 |
| `tickers_dow()` | Wikipedia | 30 只道琼斯成分股 |
| `tickers_amex()` | nasdaqtrader.com (Exchange='A') | ~300 只 AMEX 股票 |

#### `ta_functions.py` — 技术指标库

50+ 指标，分类如下：

- **趋势**：SMA, EMA, WMA, MACD, ADX, LINEARREG
- **波动**：BBANDS, ATR, NATR, STDDEV, TRANGE
- **动量**：RSI, CCI, STOCH, MOM, ROC, WILLR
- **量能**：OBV, AD, ADOSC, MFI
- **数学运算**：ADD, SUB, MULT, DIV, MAX, MIN, SUM, BETA

### 3.4 模块详解

#### `find_stocks/` — 选股筛选器

| 脚本 | 策略/方法 |
|------|-----------|
| `minervini_screener.py` | **Minervini 趋势模板**：价格>150日/200日均线、150日均线>200日均线、价格>50日均线、价格≥1.3×52周低点、价格≥0.75×52周高点，按 RS 排名 |
| `IBD_RS_Rating.py` | **IBD 相对强度评级**：与 S&P500 比较收益，近季度权重 2x，1-99 评级排名 |
| `fundamental_screener.py` | **基本面筛选**：ROE/ROA/营收增长/净利润增长加权评分 |
| `finviz_growth_screener.py` | Finviz 成长股筛选 |
| `get_rsi_tickers.py` | RSI 超买超卖筛选 |
| `green_line_values.py` | 关键支撑位突破筛选 |
| `stock_news_sentiment.py` | 新闻情绪筛选 |
| `tradingview_signals.py` | TradingView 买卖信号 |
| `twitter_screener.py` | Twitter 社交媒体情绪 |
| `yahoo_recommendations.py` | Yahoo 分析师推荐 |

#### `machine_learning/` — 机器学习模型

| 脚本 | 算法 | 实现要点 |
|------|------|----------|
| `lstm_prediction.py` | **LSTM 神经网络** | 60天回望窗口，2层LSTM(50神经元)，80/20分割，预测次日收盘价 |
| `prophet_price_prediction.py` | **Facebook Prophet** | 自动处理季节性，30天前瞻预测 |
| `kmeans_clustering.py` | **K-Means 聚类** | 按年化收益/波动率聚类道琼斯成分股，肘部法则选K |
| `arima_time_series.py` | **ARIMA/SARIMA** | 差分时间序列预测 |
| `neural_network_prediction.py` | **多层感知机** | 多隐藏层深度神经网络 |
| `pca_kmeans_clustering.py` | **PCA + K-Means** | 降维后聚类 |
| `ml_models_accuracy.py` | **多模型对比** | 比较多种 ML 模型准确率 |
| `deep_learning_bot.py` | **深度学习交易机器人** | 自动化交易决策 |
| `stock_regression_analysis.py` | **回归分析** | 线性/非线性回归 |

#### `portfolio_strategies/` — 投资组合策略

| 脚本 | 策略 | 实现要点 |
|------|------|----------|
| `monte_carlo.py` | **蒙特卡洛模拟** | 基于历史 CAGR 和波动率，1000+ 路径模拟，5%/95%置信区间 |
| `portfolio_optimization.py` | **有效前沿优化** | scipy.optimize 约束优化，最大夏普比率/最小波动率组合，pypfopt 离散配置 |
| `ema_crossover_strategy.py` | **EMA 交叉策略** | EMA20 交叉信号，等权持仓，累积对数收益 |
| `pairs_trading.py` | **配对交易** | 统计套利，相关性检测 |
| `geometric_brownian_motion.py` | **几何布朗运动** | 随机过程建模 |
| `portfolio_var_simulation.py` | **VaR 模拟** | 风险价值计算 |
| `risk_management.py` | **风险管理** | 止损/仓位管理/回撤分析 |
| `optimal_portfolio.py` | **最优组合** | 多目标优化 |
| `backtest_strategies.py` | **通用回测框架** | 策略回测引擎 |
| `support_resistance_finder.py` | **支撑/阻力位** | 自动识别关键价位 |

#### `stock_analysis/` — 个股分析

| 脚本 | 方法 | 实现要点 |
|------|------|----------|
| `intrinsic_value.py` | **DCF 估值** | Financial Modeling Prep 财报数据，3阶段增长模型，20年预测，计算内在价值 |
| `capm_analysis.py` | **CAPM 模型** | 回归法求 beta，无风险利率 2%，计算期望收益 |
| `kelly_criterion.py` | **凯利公式** | 胜率 × 盈亏比计算最优仓位比例 |
| `var_analysis.py` | **VaR 分析** | 风险价值计算 |
| `seasonal_stock_analysis.py` | **季节性分析** | 检测周期性价格模式 |
| `earnings_call_sentiment_analysis.py` | **财报电话会 NLP** | 情绪分析 |
| `twitter_sentiment_analysis.py` | **推特情绪分析** | 社交媒体情绪 |
| `performance_risk_analysis.py` | **绩效风险分析** | 夏普比率/索提诺比率/最大回撤 |

#### `stock_data/` — 数据采集

| 脚本 | 数据源 | 采集内容 |
|------|--------|----------|
| `finviz_stock_scraper.py` | Finviz | 基本面指标、新闻、内部交易 |
| `fundamental_ratios.py` | FundamentalAnalysis 库 | P/E/ROE/负债率等多年历史 |
| `historical_sp500_data.py` | Yahoo Finance | 10年 OHLCV，按 ticker 存 CSV |
| `finviz_news_scraper.py` | Finviz | 实时新闻聚合 |
| `finviz_insider_trades.py` | Finviz | 内部人交易记录 |
| `high_dividend_yield.py` | 多源 | 高股息股票筛选 |
| `dividend_history.py` | Yahoo Finance | 历史分红记录 |

### 3.5 关键依赖

| 类别 | 库 |
|------|-----|
| 数据 | pandas, numpy, yfinance, pandas-datareader |
| ML/DL | scikit-learn, tensorflow/keras, statsmodels, fbprophet |
| 优化 | scipy.optimize, pypfopt |
| 可视化 | matplotlib, seaborn, mplfinance |
| 爬虫 | beautifulsoup4, selenium, autoscraper |
| 技术分析 | ta (TALib) |
| 社交 | praw (Reddit), tweepy (Twitter), vaderSentiment |
| 通知 | twilio (SMS) |

---

## 四、两个项目的对比

| 维度 | Ashare-main | Finance-master |
|------|-------------|----------------|
| **市场** | 中国 A 股 | 美股 |
| **数据源** | 新浪财经 + 腾讯股票 | Yahoo Finance + Finviz + FMP API |
| **架构** | 单文件库（import 即用） | 150+ 独立脚本 |
| **技术指标** | MyTT（30+ 指标，公式化） | ta_functions.py（50+ 指标）+ ta 库 |
| **ML/AI** | 无 | LSTM/Prophet/ARIMA/K-Means 等 |
| **策略回测** | 无（仅提供数据） | Monte Carlo/EMA交叉/配对交易等 |
| **选股** | 无 | Minervini/IBD/基本面/情绪筛选 |
| **估值** | 无 | DCF/CAPM/Kelly 公式 |
| **适合场景** | A 股量化研究的数据层 | 美股全流程量化分析学习 |

---

## 五、典型使用模式

### Ashare 数据获取 + 指标计算

```python
from Ashare import get_price
from MyTT import MACD, BOLL, KDJ

df = get_price('sh600519', frequency='1d', count=120)
CLOSE, HIGH, LOW = df.close.values, df.high.values, df.low.values

dif, dea, macd = MACD(CLOSE)          # MACD 指标
upper, mid, lower = BOLL(CLOSE)        # 布林带
k, d, j = KDJ(CLOSE, HIGH, LOW)       # KDJ 指标
```

### Finance-master 选股 → 分析 → 策略

```
1. tickers.py          → 获取 S&P500 成分股列表
2. minervini_screener   → 筛选符合趋势模板的股票
3. intrinsic_value      → DCF 估值判断是否低估
4. lstm_prediction      → ML 预测未来走势
5. portfolio_optimization → 优化持仓权重
6. monte_carlo          → 模拟风险评估
```

---

## 六、开发注意事项

1. **Ashare API 可能不稳定**：新浪/腾讯接口为非官方 API，可能随时变更。代码已有双源容灾，但需关注接口可用性。
2. **Finance-master 需要 API Key**：部分脚本（`intrinsic_value.py`、`fundamental_screener.py`）依赖 Financial Modeling Prep API key。
3. **爬虫合规**：Finviz/Reddit/Twitter 爬取需遵守各平台 ToS。
4. **数据延迟**：实时数据存在 15 分钟延迟（免费数据源限制）。
5. **MyTT 的 SMA 函数**：需要至少 120 个数据点才能保证精度（alpha=M/N 的指数加权特性）。

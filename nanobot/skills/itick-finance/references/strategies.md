# 选股策略参考

## 一夜持股法

短线策略，适合日内至隔日的短期操作。

### 筛选条件 (9项量化指标)

| # | 条件 | 参数 | API/计算方式 |
|---|------|------|-------------|
| 1 | 涨幅 3%-5% | `chp` 字段 | /stock/quote → `chp` |
| 2 | 量比 > 1 | 当日量 / 5日均量 | /stock/quote `v` ÷ /stock/kline 近5日 `v` 平均 |
| 3 | 流通市值 50-200亿 | `mcb` 字段 | /stock/info → `mcb` (单位: 元, 需÷1e8转亿) |
| 4 | 换手率 5%-10% | 成交量/总股本 | /stock/quote `v` ÷ /stock/info `tso` × 100% |
| 5 | 成交量持续放大 | 最近3日 | /stock/kline kType=8 limit=3，检查 v 递增 |
| 6 | 均线多头排列 | MA5>MA10>MA20>MA60 | /stock/kline kType=8 limit=60，计算各MA |
| 7 | 股价在均线上方 | 价格 > MA5,10,20 | 当前价 vs 各MA值 |
| 8 | 高于VWAP且强于大盘 | 分时VWAP | /stock/kline kType=1 计算VWAP |
| 9 | 走势强于大盘 | 个股涨幅 > 大盘涨幅 | 比较 chp |

### 操作规则

- **入场时间**: 下午 14:30 后
- **出场时间**: 次日 14:30 前
- **止损**: -3%
- **通过阈值**: 满足 ≥ 7/9 项为强烈推荐，5-6项为关注

### AI 调用流程

当用户要求使用"一夜持股法"筛选股票时，按以下步骤:

**步骤1: 获取大盘基准 (上证指数)**
```
web_fetch(url="https://api.itick.org/stock/quote?region=SH&code=000001", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```
记录大盘 `chp` 值作为 benchmark_chp。

**步骤2: 对每只候选股票获取数据**

需要4个API调用:
```
# 实时行情
web_fetch(url="https://api.itick.org/stock/quote?region={region}&code={code}", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})

# 日K线 (60根用于均线计算)
web_fetch(url="https://api.itick.org/stock/kline?region={region}&code={code}&kType=8&limit=60", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})

# 1分钟K线 (当日分时用于VWAP)
web_fetch(url="https://api.itick.org/stock/kline?region={region}&code={code}&kType=1&limit=240", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})

# 公司信息 (市值、股本)
web_fetch(url="https://api.itick.org/stock/info?type=stock&region={region}&code={code}", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

**步骤3: 运行筛选脚本**
```python
# 通过 exec 执行以下 Python 代码
import json, sys
sys.path.insert(0, 'skills/itick-finance/scripts')
from screener import screen_stock, format_result

result = screen_stock(
    quote=quote_data,       # /stock/quote 返回的 data
    klines_day=klines_day,  # /stock/kline kType=8 返回的 data 数组
    klines_1min=klines_1m,  # /stock/kline kType=1 返回的 data 数组
    info=info_data,         # /stock/info 返回的 data
    benchmark_chp=0.5       # 大盘涨跌幅
)
print(format_result(result))
```

**步骤4: 汇总结果**

将所有通过筛选的股票整理成表格:

| 股票 | 涨幅 | 量比 | 市值(亿) | 换手率 | 评分 | 结论 |
|------|------|------|---------|--------|------|------|
| xxx  | x.x% | x.x | xxx | x.x% | x/9 | 推荐/关注 |

### 注意事项

- 此策略仅供参考，不构成投资建议
- 需在交易日 14:30 后执行才有实际意义
- 非交易时间可用于回测历史数据
- 建议配合大盘走势综合判断
- iTick 免费版有 API 调用频率限制，批量筛选时注意间隔

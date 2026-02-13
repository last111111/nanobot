---
name: itick-finance
description: "通过iTick API查询全球股票(A股/港股/美股)实时行情、K线数据、盘口深度、IPO信息，并进行技术分析和选股策略筛选。当用户提到以下内容时触发：股票、行情、K线、涨跌、A股、港股、美股、盘口、IPO、技术分析、MACD、RSI、均线、选股、筛选、一夜持股。"
metadata: {"nanobot":{"triggers":["股票","行情","K线","涨跌","A股","港股","美股","盘口","IPO","技术分析","MACD","RSI","均线","选股","筛选","一夜持股","itick","stock","kline"],"secrets":{"ITICK_TOKEN":"~/.nanobot/itick_token.txt"}}}
---
# iTick 金融数据

通过 iTick API 获取全球股票实时数据。支持 A 股、港股、美股及全球 20+ 市场。

**认证方式**: 所有 API 请求必须在 headers 中携带 `token` 字段。Token 值已自动注入，直接使用即可。

**所有 web_fetch 调用必须包含以下 headers:**
```
headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"}
```

**Base URL**: `https://api.itick.org`

## 市场代码 (region)

| 代码 | 市场 | 代码 | 市场   |
| ---- | ---- | ---- | ------ |
| SH   | 上证 | SZ   | 深证   |
| HK   | 港股 | US   | 美股   |
| JP   | 日本 | SG   | 新加坡 |
| TW   | 台湾 | DE   | 德国   |
| GB   | 英国 | FR   | 法国   |
| KR   | 韩国 | AU   | 澳洲   |
| IN   | 印度 | TH   | 泰国   |

A 股代码：上证用 region=SH（如 600519），深证用 region=SZ（如 000001）。

## 实时行情

**单只股票报价:**

```
web_fetch(url="https://api.itick.org/stock/quote?region=SH&code=600519", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

返回字段: `ld`=最新价, `o`=开盘价, `p`=前收, `h`=最高, `l`=最低, `v`=成交量, `tu`=成交额, `ch`=涨跌额, `chp`=涨跌幅(%), `ts`=交易状态(0正常/1停牌/2退市/3熔断)

**批量报价（多只股票）:**

```
web_fetch(url="https://api.itick.org/stock/quotes?region=SH&codes=600519,601318,600036", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

返回以股票代码为 key 的对象，每只股票字段同上。

## K 线历史数据

**单只股票 K 线:**

```
web_fetch(url="https://api.itick.org/stock/kline?region=SH&code=600519&kType=8&limit=30", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

kType 周期: 1=1分钟, 2=5分钟, 3=15分钟, 4=30分钟, 5=1小时, 8=日K, 9=周K, 10=月K
返回数组，每项: `o`=开盘, `c`=收盘, `h`=最高, `l`=最低, `v`=成交量, `tu`=成交额, `t`=时间戳(ms)
可选参数: `et`=截止时间戳(ms), `limit`=返回条数

**批量 K 线（多只股票）:**

```
web_fetch(url="https://api.itick.org/stock/klines?region=SH&codes=600519,601318&kType=8&limit=30", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

## 盘口深度

**买卖盘:**

```
web_fetch(url="https://api.itick.org/stock/depth?region=SH&code=600519", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

返回: `a`=卖盘(ask), `b`=买盘(bid)，每档含 `po`=档位, `p`=价格, `v`=数量, `o`=订单数

## 逐笔成交

```
web_fetch(url="https://api.itick.org/stock/tick?region=SH&code=600519", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

返回: `ld`=最新价, `v`=成交量, `t`=时间戳, `te`=交易时段(0正常/1盘前/2盘后)

## 公司信息

```
web_fetch(url="https://api.itick.org/stock/info?type=stock&region=SH&code=600519", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

返回: `n`=名称, `e`=交易所, `s`=板块, `i`=行业, `mcb`=总市值, `tso`=总股本, `pet`=市盈率

## IPO 新股

```
web_fetch(url="https://api.itick.org/stock/ipo?type=upcoming&region=SH", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

type: `upcoming`=即将上市, `recent`=近期上市
返回: `cn`=公司名, `sc`=股票代码, `ex`=交易所, `mc`=市值, `pr`=价格区间, `dt`=上市日期

## 复权因子

```
web_fetch(url="https://api.itick.org/stock/split?region=SH", headers={"token": "{{ITICK_TOKEN}}", "accept": "application/json"})
```

返回: `n`=股票名, `c`=代码, `v`=复权因子(如"1:10"), `d`=复权日期

## 技术分析

获取 K 线数据后，用 exec 运行 Python 计算技术指标。

**使用内置指标模块 (推荐):**

```python
import sys, json
sys.path.insert(0, 'skills/itick-finance/scripts')
from indicators import full_analysis, extract_ohlcv

# klines 是从 /stock/kline 获取的 data 数组
result = full_analysis(klines, name="贵州茅台")
print(json.dumps(result, ensure_ascii=False, indent=2))
```

返回: MA5/10/20/60, RSI14, MACD(DIF/DEA/HIST), KDJ, 布林带, 量比, 均线多头排列, 量能趋势。

更多分析方法(MACD/布林带/KDJ)见 references/analysis.md。

## 选股策略

**一夜持股法** - 短线策略，9项量化条件筛选:

涨幅3-5% + 量比>1 + 市值50-200亿 + 换手率5-10% + 量能放大 + 均线多头 + 价在均线上 + 高于VWAP + 强于大盘

调用方式:

```python
import sys, json
sys.path.insert(0, 'skills/itick-finance/scripts')
from screener import screen_stock, format_result

result = screen_stock(
    quote=quote_data,        # /stock/quote 的 data
    klines_day=klines_day,   # /stock/kline kType=8 limit=60 的 data
    klines_1min=klines_1min, # /stock/kline kType=1 limit=240 的 data
    info=info_data,          # /stock/info 的 data
    benchmark_chp=0.5        # 大盘涨跌幅(从上证指数获取)
)
print(format_result(result))
```

详细策略说明和完整调用流程见 references/strategies.md。

## 参考文档索引

| 文档                     | 内容                                          |
| ------------------------ | --------------------------------------------- |
| references/api-fields.md | API 完整字段映射                              |
| references/analysis.md   | 技术指标计算方法 (MA/EMA/MACD/RSI/KDJ/布林带) |
| references/strategies.md | 选股策略 (一夜持股法完整流程)                 |
| scripts/indicators.py    | 可复用技术指标模块                            |
| scripts/screener.py      | 一夜持股法筛选脚本                            |

## 注意事项

- A 股交易时间: 工作日 9:30-11:30, 13:00-15:00 (北京时间)
- 港股交易时间: 工作日 9:30-12:00, 13:00-16:00
- 美股交易时间: 工作日 9:30-16:00 (美东时间)，有盘前盘后
- 非交易时间返回最近交易日数据
- 所有时间戳单位为毫秒
- 选股策略仅供参考，不构成投资建议

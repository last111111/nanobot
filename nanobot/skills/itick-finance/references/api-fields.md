# iTick API 完整字段参考

## 通用请求头

所有请求需携带:
```
accept: application/json
token: {Your iTick Token}
```

## 通用响应结构

```json
{
  "code": 0,       // 0=成功
  "msg": "ok",     // 响应描述
  "data": { ... }  // 数据体
}
```

---

## 1. 实时报价 /stock/quote

**请求**: `GET /stock/quote?region={region}&code={code}`

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| s | string | 标的代码 |
| ld | number | 最新价 |
| o | number | 开盘价 |
| p | number | 前日收盘价 |
| h | number | 最高价 |
| l | number | 最低价 |
| t | number | 最新成交时间戳(ms) |
| v | number | 成交数量 |
| tu | number | 成交额 |
| ts | number | 交易状态: 0=正常, 1=停牌, 2=退市, 3=熔断 |
| ch | number | 涨跌额 |
| chp | number | 涨跌幅(%) |

## 2. 批量报价 /stock/quotes

**请求**: `GET /stock/quotes?region={region}&codes={code1,code2,...}`

返回以股票代码为 key 的对象，每个 value 字段同 /stock/quote。

## 3. K 线数据 /stock/kline

**请求**: `GET /stock/kline?region={region}&code={code}&kType={kType}&limit={limit}&et={timestamp}`

**请求参数:**

| 参数 | 必填 | 说明 |
|------|------|------|
| region | 是 | 市场代码 |
| code | 是 | 股票代码 |
| kType | 是 | 周期类型(见下表) |
| limit | 是 | 返回条数 |
| et | 否 | 截止时间戳(ms)，默认当前 |

**kType 周期对照表:**

| kType | 周期 |
|-------|------|
| 1 | 1 分钟 |
| 2 | 5 分钟 |
| 3 | 15 分钟 |
| 4 | 30 分钟 |
| 5 | 1 小时 |
| 8 | 日 K |
| 9 | 周 K |
| 10 | 月 K |

**响应字段 (data 数组):**

| 字段 | 类型 | 说明 |
|------|------|------|
| o | number | 开盘价 |
| c | number | 收盘价 |
| h | number | 最高价 |
| l | number | 最低价 |
| v | number | 成交量 |
| tu | number | 成交额 |
| t | number | 时间戳(ms) |

## 4. 批量 K 线 /stock/klines

**请求**: `GET /stock/klines?region={region}&codes={code1,code2}&kType={kType}&limit={limit}`

返回以股票代码为 key 的对象，每个 value 为 K 线数组，字段同 /stock/kline。

## 5. 盘口深度 /stock/depth

**请求**: `GET /stock/depth?region={region}&code={code}`

**响应字段:**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | 标的代码 |
| a | array | 卖盘(Ask)数组 |
| b | array | 买盘(Bid)数组 |

**买卖盘每档字段:**

| 字段 | 类型 | 说明 |
|------|------|------|
| po | number | 档位(1-10) |
| p | number | 价格 |
| v | number | 数量 |
| o | number | 订单数 |

## 6. 逐笔成交 /stock/tick

**请求**: `GET /stock/tick?region={region}&code={code}`

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| s | string | 标的代码 |
| ld | number | 最新成交价 |
| t | number | 成交时间戳(ms) |
| v | number | 成交量 |
| te | number | 交易时段: 0=正常, 1=盘前, 2=盘后 |

## 7. 公司信息 /stock/info

**请求**: `GET /stock/info?type=stock&region={region}&code={code}`

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| c | string | 股票代码 |
| n | string | 公司名称 |
| t | string | 类型 |
| e | string | 交易所 |
| s | string | 所属板块 |
| i | string | 所属行业 |
| r | string | 区域代码 |
| bd | string | 公司简介 |
| wu | string | 公司网站 |
| mcb | number | 总市值 |
| tso | number | 总股本 |
| pet | number | 市盈率(PE) |
| fcc | string | 货币代码 |

## 8. IPO 新股 /stock/ipo

**请求**: `GET /stock/ipo?type={type}&region={region}`

**请求参数:**

| 参数 | 说明 |
|------|------|
| type | `upcoming`=即将上市, `recent`=近期上市 |
| region | 市场代码 |

**响应字段 (data.content 数组):**

| 字段 | 类型 | 说明 |
|------|------|------|
| cn | string | 公司名称 |
| sc | string | 股票代码 |
| ex | string | 交易所 |
| mc | string | 市值 |
| pr | string | 价格区间 |
| ct | string | 国家代码 |
| dt | number | 上市日期时间戳(ms) |
| bs | number | 认购开始时间(s) |
| es | number | 认购结束时间(s) |
| ro | number | 中签公布时间(s) |

分页字段: `page`, `totalElements`, `totalPages`, `last`, `size`

## 9. 复权因子 /stock/split

**请求**: `GET /stock/split?region={region}`

**响应字段 (data.content 数组):**

| 字段 | 类型 | 说明 |
|------|------|------|
| n | string | 股票名称 |
| c | string | 股票代码 |
| r | string | 市场代码 |
| v | string | 复权因子(如 "1:10") |
| d | number | 复权日期时间戳(ms) |

分页字段: `page`, `totalElements`, `totalPages`, `last`, `size`

---

## 市场代码完整列表

| 代码 | 市场 | 代码 | 市场 |
|------|------|------|------|
| SH | 上海证券交易所 | SZ | 深圳证券交易所 |
| HK | 香港交易所 | US | 美国(NYSE/NASDAQ) |
| JP | 日本(东京) | SG | 新加坡 |
| TW | 台湾 | IN | 印度 |
| TH | 泰国 | DE | 德国 |
| MX | 墨西哥 | MY | 马来西亚 |
| TR | 土耳其 | ES | 西班牙 |
| NL | 荷兰 | GB | 英国 |
| ID | 印度尼西亚 | VN | 越南 |
| KR | 韩国 | IT | 意大利 |
| FR | 法国 | AU | 澳大利亚 |
| AR | 阿根廷 | IL | 以色列 |
| PK | 巴基斯坦 | CA | 加拿大 |
| PE | 秘鲁 | NG | 尼日利亚 |

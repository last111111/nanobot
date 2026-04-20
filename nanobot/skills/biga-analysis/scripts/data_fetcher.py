# -*- coding: utf-8 -*-
"""
A股行情数据获取模块
移植自 Ashare (https://github.com/mpquant/Ashare)
双数据源: 新浪财经(主) + 腾讯股票(备), 自动容灾切换
"""

import json
import datetime
import requests
import pandas as pd

REQUEST_TIMEOUT = 10


def _load_json(url):
    """Fetch and decode JSON payloads with a bounded timeout."""
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return json.loads(response.content)


def get_price_day_tx(code, end_date='', count=10, frequency='1d'):
    """腾讯日/周/月线数据"""
    unit = 'week' if frequency == '1w' else 'month' if frequency == '1M' else 'day'
    if end_date:
        end_date = end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime.date) else end_date.split(' ')[0]
    end_date = '' if end_date == datetime.datetime.now().strftime('%Y-%m-%d') else end_date
    URL = f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},{unit},,{end_date},{count},qfq'
    st = _load_json(URL)
    ms = 'qfq' + unit
    stk = st['data'][code]
    buf = stk[ms] if ms in stk else stk[unit]
    df = pd.DataFrame(buf, columns=['time', 'open', 'close', 'high', 'low', 'volume'], dtype='float')
    df.time = pd.to_datetime(df.time)
    df.set_index(['time'], inplace=True)
    df.index.name = ''
    return df


def get_price_min_tx(code, end_date=None, count=10, frequency='1d'):
    """腾讯分钟线数据"""
    ts = int(frequency[:-1]) if frequency[:-1].isdigit() else 1
    if end_date:
        end_date = end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime.date) else end_date.split(' ')[0]
    URL = f'http://ifzq.gtimg.cn/appstock/app/kline/mkline?param={code},m{ts},,{count}'
    st = _load_json(URL)
    buf = st['data'][code]['m' + str(ts)]
    df = pd.DataFrame(buf, columns=['time', 'open', 'close', 'high', 'low', 'volume', 'n1', 'n2'])
    df = df[['time', 'open', 'close', 'high', 'low', 'volume']]
    df[['open', 'close', 'high', 'low', 'volume']] = df[['open', 'close', 'high', 'low', 'volume']].astype('float')
    df.time = pd.to_datetime(df.time)
    df.set_index(['time'], inplace=True)
    df.index.name = ''
    df.iloc[-1, df.columns.get_loc('close')] = float(st['data'][code]['qt'][code][3])
    return df


def get_price_sina(code, end_date='', count=10, frequency='60m'):
    """新浪全周期数据 (分钟/日/周/月)"""
    frequency = frequency.replace('1d', '240m').replace('1w', '1200m').replace('1M', '7200m')
    mcount = count
    ts = int(frequency[:-1]) if frequency[:-1].isdigit() else 1
    if (end_date != '') & (frequency in ['240m', '1200m', '7200m']):
        end_date = pd.to_datetime(end_date) if not isinstance(end_date, datetime.date) else end_date
        unit = 4 if frequency == '1200m' else 29 if frequency == '7200m' else 1
        count = count + (datetime.datetime.now() - end_date).days // unit
    URL = (f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/'
           f'CN_MarketData.getKLineData?symbol={code}&scale={ts}&ma=5&datalen={count}')
    dstr = _load_json(URL)
    df = pd.DataFrame(dstr, columns=['day', 'open', 'high', 'low', 'close', 'volume'])
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df.day = pd.to_datetime(df.day)
    df.set_index(['day'], inplace=True)
    df.index.name = ''
    if (end_date != '') & (frequency in ['240m', '1200m', '7200m']):
        return df[df.index <= end_date][-mcount:]
    return df


def get_price(code, end_date='', count=10, frequency='1d'):
    """
    获取A股行情数据 (统一入口)

    Parameters:
        code: 证券代码, 支持格式:
              - sh600519 / sz000001 (通达信格式)
              - 600519.XSHG / 000001.XSHE (聚宽格式)
        end_date: 结束日期, 如 '2024-01-01', 默认为最新
        count: K线数量, 默认10
        frequency: K线周期
              - '1d' 日线, '1w' 周线, '1M' 月线
              - '1m' '5m' '15m' '30m' '60m' 分钟线

    Returns:
        DataFrame: columns=[open, close, high, low, volume], index=datetime
    """
    xcode = code.replace('.XSHG', '').replace('.XSHE', '')
    xcode = 'sh' + xcode if ('XSHG' in code) else 'sz' + xcode if ('XSHE' in code) else code

    providers = []
    if frequency in ['1d', '1w', '1M']:
        providers = [
            ("sina", get_price_sina),
            ("tencent", get_price_day_tx),
        ]
    elif frequency in ['1m', '5m', '15m', '30m', '60m']:
        providers = [
            ("tencent", get_price_min_tx),
        ] if frequency == '1m' else [
            ("sina", get_price_sina),
            ("tencent", get_price_min_tx),
        ]
    else:
        raise ValueError(f'不支持的频率: {frequency}')

    errors = []
    for provider_name, provider in providers:
        try:
            return provider(xcode, end_date=end_date, count=count, frequency=frequency)
        except Exception as exc:
            errors.append(f'{provider_name}: {exc}')

    raise RuntimeError(' ; '.join(errors))

# -*- coding: utf-8 -*-
"""
A股技术指标分析 - 可执行脚本
用法:
    python run.py sh600519                          # 茅台日线, 默认全部指标
    python run.py sh600519 --freq 15m --count 60    # 15分钟线, 60根K线
    python run.py sz000001 --indicators MACD,RSI,KDJ,BBANDS
    python run.py sh000001 --list                   # 列出所有可用指标
    python run.py sh600519 --json                   # JSON输出 (方便LLM解析)

数据源: 新浪财经 + 腾讯股票 (双核心自动容灾)
"""

import sys
import os
import json
import argparse

import numpy as np
import pandas as pd

# 支持直接运行和模块导入两种方式
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import get_price
from ta_functions import INDICATOR_REGISTRY


def compute_indicator(name, df):
    """
    根据指标名计算指标值

    Args:
        name: 指标名 (如 'MACD', 'RSI')
        df: 行情DataFrame, 含 open/close/high/low/volume 列

    Returns:
        dict: {指标名: 值(最近一条)} 或 {子指标名: 值} (多返回值指标)
    """
    info = INDICATOR_REGISTRY.get(name)
    if not info:
        return {name: f'未知指标: {name}'}

    # 准备参数
    param_map = {
        'open': df['open'], 'close': df['close'],
        'high': df['high'], 'low': df['low'], 'volume': df['volume'],
    }
    args = [param_map[p] for p in info['params']]

    try:
        result = info['func'](*args)
    except Exception as e:
        return {name: f'计算失败: {e}'}

    # 处理返回值 (单值或元组)
    if isinstance(result, tuple):
        return _unpack_tuple(name, result)
    else:
        val = _last_valid(result)
        return {name: val}


def _unpack_tuple(name, result):
    """拆解多返回值指标"""
    sub_names = {
        'MACD':   ('MACD_DIF', 'MACD_DEA', 'MACD_HIST'),
        'KDJ':    ('KDJ_K', 'KDJ_D', 'KDJ_J'),
        'STOCH':  ('STOCH_SLOWK', 'STOCH_SLOWD'),
        'DMI':    ('DMI_PDI', 'DMI_MDI', 'DMI_ADX', 'DMI_ADXR'),
        'BBANDS': ('BBANDS_UPPER', 'BBANDS_MID', 'BBANDS_LOWER'),
        'WR':     ('WR_10', 'WR_6'),
        'BIAS':   ('BIAS_6', 'BIAS_12', 'BIAS_24'),
        'MTM':    ('MTM', 'MTM_MA'),
        'PSY':    ('PSY', 'PSY_MA'),
        'DPO':    ('DPO', 'DPO_MA'),
        'DMA':    ('DMA_DIF', 'DMA_DIFMA'),
        'TRIX':   ('TRIX', 'TRIX_MA'),
        'EMV':    ('EMV', 'EMV_MA'),
        'BRAR':   ('BRAR_AR', 'BRAR_BR'),
        'TAQ':    ('TAQ_UP', 'TAQ_MID', 'TAQ_DOWN'),
    }

    keys = sub_names.get(name)
    if keys and len(keys) == len(result):
        return {k: _last_valid(v) for k, v in zip(keys, result)}
    else:
        return {f'{name}_{i}': _last_valid(v) for i, v in enumerate(result)}


def _last_valid(series):
    """取序列最后一个有效值, 转为 Python float"""
    if isinstance(series, (pd.Series, np.ndarray)):
        s = pd.Series(series)
        last = s.dropna().iloc[-1] if not s.dropna().empty else None
        return round(float(last), 4) if last is not None else None
    return round(float(series), 4) if series is not None else None


def _format_last_time(timestamp, frequency):
    """Format timestamps consistently for day and minute bars."""
    ts = pd.Timestamp(timestamp)
    if frequency.endswith('m'):
        return ts.strftime('%Y-%m-%d %H:%M:%S')
    return ts.strftime('%Y-%m-%d')


def _error_result(code, frequency, count, message):
    """Build a stable machine-readable error payload."""
    return {
        'error': message,
        'price': {
            'code': code,
            'frequency': frequency,
            'count': count,
        },
        'indicators': {},
    }


def analyze(code, frequency='1d', count=120, indicators=None):
    """
    获取行情 + 计算技术指标

    Args:
        code: 证券代码 (sh600519 / 600519.XSHG 等)
        frequency: K线周期 ('1d', '1w', '1M', '5m', '15m', '30m', '60m')
        count: K线数量
        indicators: 指标列表, None=全部计算

    Returns:
        dict: 完整分析结果 (可直接 json.dumps)
    """
    # 获取数据
    try:
        df = get_price(code, count=count, frequency=frequency)
    except Exception as e:
        return _error_result(code, frequency, count, f'获取行情失败: {e}')

    if df is None or df.empty:
        return _error_result(code, frequency, count, f'无法获取 {code} 的行情数据')

    # 确定要计算的指标
    if indicators is None:
        indicators = list(INDICATOR_REGISTRY.keys())
    else:
        indicators = [i.strip().upper() for i in indicators if i.strip()]

    # 计算所有指标
    results = {}
    for name in indicators:
        results.update(compute_indicator(name, df))

    # 最新行情快照
    last = df.iloc[-1]
    price_info = {
        'code': code,
        'frequency': frequency,
        'last_time': _format_last_time(df.index[-1], frequency),
        'open': round(float(last['open']), 4),
        'close': round(float(last['close']), 4),
        'high': round(float(last['high']), 4),
        'low': round(float(last['low']), 4),
        'volume': round(float(last['volume']), 2),
        'count': len(df),
    }

    return {
        'price': price_info,
        'indicators': results,
    }


def format_table(data):
    """格式化为可读文本表格"""
    if 'error' in data:
        price = data.get('price', {})
        return (
            f"获取失败: {data['error']}\n"
            f"证券代码: {price.get('code', '?')}  周期: {price.get('frequency', '?')}"
        )

    lines = []
    price = data.get('price', {})
    lines.append(f"{'='*50}")
    lines.append(f"  {price.get('code', '?')}  |  {price.get('frequency', '?')}  |  {price.get('last_time', '?')}")
    lines.append(f"  开: {price.get('open')}  高: {price.get('high')}  低: {price.get('low')}  收: {price.get('close')}  量: {price.get('volume')}")
    lines.append(f"{'='*50}")

    indicators = data.get('indicators', {})
    for k, v in indicators.items():
        if v is None:
            lines.append(f"  {k:16s}:  N/A")
        elif isinstance(v, str):
            lines.append(f"  {k:16s}:  {v}")
        else:
            lines.append(f"  {k:16s}:  {v}")
    lines.append(f"{'='*50}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='A股技术指标分析工具')
    parser.add_argument('code', nargs='?', help='证券代码 (如 sh600519, 000001.XSHG)')
    parser.add_argument('--freq', '-f', default='1d', help='K线周期: 1d/1w/1M/1m/5m/15m/30m/60m (默认1d)')
    parser.add_argument('--count', '-c', type=int, default=120, help='K线数量 (默认120)')
    parser.add_argument('--indicators', '-i', default=None, help='指定指标, 逗号分隔 (如 MACD,RSI,KDJ)')
    parser.add_argument('--json', '-j', action='store_true', help='JSON格式输出 (方便LLM解析)')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有可用指标')

    args = parser.parse_args()

    # 列出指标
    if args.list:
        print(f"\n{'指标名':12s}  {'说明'}")
        print(f"{'-'*40}")
        for name, info in INDICATOR_REGISTRY.items():
            params = ', '.join(info['params'])
            print(f"  {name:10s}  {info['desc']:16s}  ({params})")
        return

    if not args.code:
        parser.print_help()
        return

    # 解析指标列表
    indicator_list = None
    if args.indicators:
        indicator_list = [i.strip().upper() for i in args.indicators.split(',')]

    # 执行分析
    result = analyze(args.code, frequency=args.freq, count=args.count, indicators=indicator_list)

    # 输出
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_table(result))

    if 'error' in result:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

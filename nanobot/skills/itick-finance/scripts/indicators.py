"""
iTick 技术指标计算模块
所有函数仅依赖 Python 标准库，可通过 exec 直接调用。
"""
import math
import json


# ============ 移动平均线 ============

def calc_ma(closes, period):
    """简单移动平均线 (SMA)"""
    return [sum(closes[i - period + 1:i + 1]) / period
            for i in range(period - 1, len(closes))]


def calc_ema(closes, period):
    """指数移动平均线 (EMA)"""
    k = 2 / (period + 1)
    ema = [closes[0]]
    for i in range(1, len(closes)):
        ema.append(closes[i] * k + ema[-1] * (1 - k))
    return ema


def calc_vwap(closes, volumes):
    """成交量加权平均价 (VWAP)"""
    cum_vol = 0
    cum_pv = 0
    vwap = []
    for c, v in zip(closes, volumes):
        cum_pv += c * v
        cum_vol += v
        vwap.append(cum_pv / cum_vol if cum_vol > 0 else c)
    return vwap


# ============ 趋势指标 ============

def calc_macd(closes, fast=12, slow=26, signal=9):
    """MACD 指标，返回 (dif, dea, macd_hist)"""
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    dif = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    dea = calc_ema(dif, signal)
    macd_hist = [2 * (dif[i] - dea[i]) for i in range(len(closes))]
    return dif, dea, macd_hist


# ============ 震荡指标 ============

def calc_rsi(closes, period=14):
    """RSI 相对强弱指数"""
    if len(closes) < period + 1:
        return []
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0, c) for c in changes[:period]]
    losses = [max(0, -c) for c in changes[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    rsi_values = []
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


def calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    """KDJ 指标，返回 (k_values, d_values, j_values)"""
    k_values, d_values, j_values = [], [], []
    k, d = 50, 50
    for i in range(n - 1, len(closes)):
        hn = max(highs[i - n + 1:i + 1])
        ln = min(lows[i - n + 1:i + 1])
        rsv = (closes[i] - ln) / (hn - ln) * 100 if hn != ln else 50
        k = (m1 - 1) / m1 * k + 1 / m1 * rsv
        d = (m2 - 1) / m2 * d + 1 / m2 * k
        j = 3 * k - 2 * d
        k_values.append(round(k, 2))
        d_values.append(round(d, 2))
        j_values.append(round(j, 2))
    return k_values, d_values, j_values


# ============ 波动指标 ============

def calc_bollinger(closes, period=20, num_std=2):
    """布林带，返回 (upper, middle, lower)"""
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


# ============ 量价分析 ============

def calc_volume_ratio(volumes, period=5):
    """量比 = 当日成交量 / 过去N日平均成交量"""
    if len(volumes) < period + 1:
        return None
    avg_vol = sum(volumes[-(period + 1):-1]) / period
    return round(volumes[-1] / avg_vol, 2) if avg_vol > 0 else None


def check_volume_increasing(volumes, n=3):
    """检查最近n根K线成交量是否持续放大"""
    if len(volumes) < n:
        return False
    recent = volumes[-n:]
    return all(recent[i] > recent[i - 1] for i in range(1, len(recent)))


# ============ 均线形态判断 ============

def check_ma_bullish_alignment(closes, periods=(5, 10, 20, 60)):
    """检查均线多头排列: MA5 > MA10 > MA20 > MA60"""
    ma_values = {}
    for p in periods:
        if len(closes) < p:
            return False, {}
        ma = calc_ma(closes, p)
        ma_values[f"MA{p}"] = round(ma[-1], 2)

    sorted_periods = sorted(periods)
    latest_mas = [ma_values[f"MA{p}"] for p in sorted_periods]
    is_bullish = all(latest_mas[i] > latest_mas[i + 1] for i in range(len(latest_mas) - 1))
    return is_bullish, ma_values


def check_price_above_mas(close, closes, periods=(5, 10, 20)):
    """检查当前价格是否在所有指定均线之上"""
    for p in periods:
        if len(closes) < p:
            return False
        ma = calc_ma(closes, p)
        if close <= ma[-1]:
            return False
    return True


# ============ 换手率 ============

def calc_turnover_rate(volume, total_shares):
    """换手率 = 成交量 / 流通股本 * 100%"""
    if total_shares and total_shares > 0:
        return round(volume / total_shares * 100, 2)
    return None


# ============ 涨跌幅 ============

def calc_change_pct(current, previous):
    """涨跌幅 = (当前价 - 前收价) / 前收价 * 100%"""
    if previous and previous > 0:
        return round((current - previous) / previous * 100, 2)
    return None


# ============ 辅助函数 ============

def extract_ohlcv(klines):
    """从K线数据中提取 opens, highs, lows, closes, volumes"""
    opens = [k['o'] for k in klines]
    highs = [k['h'] for k in klines]
    lows = [k['l'] for k in klines]
    closes = [k['c'] for k in klines]
    volumes = [k['v'] for k in klines]
    return opens, highs, lows, closes, volumes


def full_analysis(klines, name=""):
    """对K线数据进行完整技术分析，返回结构化结果"""
    opens, highs, lows, closes, volumes = extract_ohlcv(klines)

    result = {"name": name}

    # 均线
    for p in [5, 10, 20, 60]:
        if len(closes) >= p:
            ma = calc_ma(closes, p)
            result[f"MA{p}"] = round(ma[-1], 2)

    # RSI
    rsi = calc_rsi(closes, 14)
    if rsi:
        result["RSI14"] = round(rsi[-1], 2)

    # MACD
    if len(closes) >= 26:
        dif, dea, macd_hist = calc_macd(closes)
        result["MACD"] = {
            "DIF": round(dif[-1], 4),
            "DEA": round(dea[-1], 4),
            "HIST": round(macd_hist[-1], 4)
        }

    # KDJ
    if len(closes) >= 9:
        k, d, j = calc_kdj(highs, lows, closes)
        result["KDJ"] = {"K": k[-1], "D": d[-1], "J": j[-1]}

    # 布林带
    if len(closes) >= 20:
        upper, middle, lower = calc_bollinger(closes)
        result["BOLL"] = {
            "upper": round(upper[-1], 2),
            "middle": round(middle[-1], 2),
            "lower": round(lower[-1], 2)
        }

    # 量比
    vr = calc_volume_ratio(volumes)
    if vr:
        result["volume_ratio"] = vr

    # 均线多头排列
    bullish, ma_dict = check_ma_bullish_alignment(closes)
    result["ma_bullish_alignment"] = bullish

    # 量能趋势
    result["volume_increasing"] = check_volume_increasing(volumes, 3)

    return result

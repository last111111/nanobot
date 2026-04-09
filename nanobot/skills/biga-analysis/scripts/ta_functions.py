# -*- coding: utf-8 -*-
"""
A股技术指标函数库
改编自 Finance-master/ta_functions.py, 适配 Ashare 数据格式
所有函数接受 pandas Series, 返回 pandas Series (保持与 DataFrame 列兼容)
"""

import numpy as np
import pandas as pd


# ==================== 移动平均类 ====================

def SMA(data, timeperiod=14):
    """简单移动平均线 (Simple Moving Average)"""
    return data.rolling(window=timeperiod).mean()


def EMA(data, timeperiod=12):
    """指数移动平均线 (Exponential Moving Average)"""
    return data.ewm(span=timeperiod, adjust=False).mean()


def WMA(data, timeperiod=10):
    """加权移动平均线 (Weighted Moving Average)"""
    weights = np.arange(1, timeperiod + 1, dtype=float)
    return data.rolling(window=timeperiod).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


# ==================== 趋势指标 ====================

def MACD(close, fastperiod=12, slowperiod=26, signalperiod=9):
    """
    MACD 指标 (Moving Average Convergence Divergence)
    Returns: (dif, dea, macd_hist)
        dif: 快线 - 慢线
        dea: dif 的信号线
        macd_hist: (dif - dea) * 2 (柱状图, 与通达信一致)
    """
    ema_fast = close.ewm(span=fastperiod, adjust=False).mean()
    ema_slow = close.ewm(span=slowperiod, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signalperiod, adjust=False).mean()
    macd_hist = (dif - dea) * 2
    return dif, dea, macd_hist


def ADX(high, low, close, timeperiod=14):
    """
    平均趋向指标 (Average Directional Index)
    衡量趋势强度, >25 表示强趋势
    """
    tr = TRANGE(high, low, close)
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0

    tr_smooth = tr.rolling(window=timeperiod).sum()
    plus_dm_smooth = plus_dm.rolling(window=timeperiod).sum()
    minus_dm_smooth = minus_dm.abs().rolling(window=timeperiod).sum()

    plus_di = 100 * (plus_dm_smooth / tr_smooth)
    minus_di = 100 * (minus_dm_smooth / tr_smooth)

    dx = 100 * np.abs((plus_di - minus_di) / (plus_di + minus_di))
    adx = dx.rolling(window=timeperiod).mean()
    return adx


def DMI(high, low, close, m1=14, m2=6):
    """
    动向指标 (Directional Movement Index)
    与通达信/同花顺一致
    Returns: (pdi, mdi, adx, adxr)
    """
    tr = pd.Series(
        np.maximum(
            np.maximum(high - low, np.abs(high - close.shift(1))),
            np.abs(low - close.shift(1))
        ),
        index=close.index
    ).rolling(m1).sum()

    hd = high - high.shift(1)
    ld = low.shift(1) - low

    dmp = pd.Series(np.where((hd > 0) & (hd > ld), hd, 0), index=close.index).rolling(m1).sum()
    dmm = pd.Series(np.where((ld > 0) & (ld > hd), ld, 0), index=close.index).rolling(m1).sum()

    pdi = dmp * 100 / tr
    mdi = dmm * 100 / tr
    adx_val = (np.abs(mdi - pdi) / (pdi + mdi) * 100).rolling(m2).mean()
    adxr = (adx_val + adx_val.shift(m2)) / 2
    return pdi, mdi, adx_val, adxr


def LINEARREG(close, timeperiod=14):
    """线性回归值"""
    idx = np.arange(timeperiod)

    def linreg(x):
        return np.polyval(np.polyfit(idx, x, 1), idx)[-1]

    return close.rolling(window=timeperiod).apply(linreg, raw=True)


def DMA(close, n1=10, n2=50, m=10):
    """
    平行线差指标
    Returns: (dif, difma)
    """
    dif = SMA(close, n1) - SMA(close, n2)
    difma = SMA(dif, m)
    return dif, difma


def TRIX(close, m1=12, m2=20):
    """
    三重指数平滑平均线
    Returns: (trix, trma)
    """
    tr = EMA(EMA(EMA(close, m1), m1), m1)
    trix = (tr - tr.shift(1)) / tr.shift(1) * 100
    trma = SMA(trix, m2)
    return trix, trma


def BBI(close, m1=3, m2=6, m3=12, m4=20):
    """多空指标 (Bull and Bear Index)"""
    return (SMA(close, m1) + SMA(close, m2) + SMA(close, m3) + SMA(close, m4)) / 4


# ==================== 震荡指标 ====================

def RSI(data, timeperiod=14):
    """
    相对强弱指数 (Relative Strength Index)
    >70 超买, <30 超卖
    """
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=timeperiod).mean()
    avg_loss = loss.rolling(window=timeperiod).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def KDJ(close, high, low, n=9, m1=3, m2=3):
    """
    KDJ 随机指标
    K>80 超买, K<20 超卖; J>100 超买, J<0 超卖
    Returns: (k, d, j)
    """
    lowest = low.rolling(n).min()
    highest = high.rolling(n).max()
    rsv = (close - lowest) / (highest - lowest) * 100
    k = rsv.ewm(span=(m1 * 2 - 1), adjust=False).mean()
    d = k.ewm(span=(m2 * 2 - 1), adjust=False).mean()
    j = k * 3 - d * 2
    return k, d, j


def STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3):
    """
    随机振荡器 (Stochastic Oscillator)
    Returns: (slowk, slowd)
    """
    highest = high.rolling(fastk_period).max()
    lowest = low.rolling(fastk_period).min()
    fastk = ((close - lowest) / (highest - lowest)) * 100
    fastd = fastk.rolling(slowk_period).mean()
    slowk = fastd.rolling(slowk_period).mean()
    slowd = slowk.rolling(slowd_period).mean()
    return slowk, slowd


def CCI(high, low, close, timeperiod=14):
    """
    商品通道指数 (Commodity Channel Index)
    >100 超买, <-100 超卖
    """
    tp = (high + low + close) / 3
    sma = tp.rolling(timeperiod).mean()
    mean_dev = np.abs(tp - sma).rolling(timeperiod).mean()
    return (tp - sma) / (0.015 * mean_dev)


def WILLR(high, low, close, timeperiod=14):
    """
    威廉指标 (Williams %R)
    -80以下超卖, -20以上超买
    """
    highest = high.rolling(window=timeperiod).max()
    lowest = low.rolling(window=timeperiod).min()
    return -100 * ((highest - close) / (highest - lowest))


def WR(close, high, low, n=10, n1=6):
    """
    W&R 威廉指标 (通达信版, 0-100)
    Returns: (wr, wr1)
    """
    wr = (high.rolling(n).max() - close) / (high.rolling(n).max() - low.rolling(n).min()) * 100
    wr1 = (high.rolling(n1).max() - close) / (high.rolling(n1).max() - low.rolling(n1).min()) * 100
    return wr, wr1


def MOM(close, timeperiod=10):
    """动量指标 (Momentum)"""
    return close.diff(periods=timeperiod)


def MTM(close, n=12, m=6):
    """
    动量指标 (通达信版)
    Returns: (mtm, mtmma)
    """
    mtm = close - close.shift(n)
    mtmma = SMA(mtm, m)
    return mtm, mtmma


def ROC(close, timeperiod=10):
    """变动率 (Rate of Change), 百分比"""
    return ((close - close.shift(timeperiod)) / close.shift(timeperiod)) * 100


def BIAS(close, l1=6, l2=12, l3=24):
    """
    乖离率 (BIAS)
    Returns: (bias1, bias2, bias3)
    """
    bias1 = (close - SMA(close, l1)) / SMA(close, l1) * 100
    bias2 = (close - SMA(close, l2)) / SMA(close, l2) * 100
    bias3 = (close - SMA(close, l3)) / SMA(close, l3) * 100
    return bias1, bias2, bias3


def PSY(close, n=12, m=6):
    """
    心理线 (Psychological Line)
    >75 过度乐观, <25 过度悲观
    Returns: (psy, psyma)
    """
    up_count = (close > close.shift(1)).astype(int).rolling(n).sum()
    psy = up_count / n * 100
    psyma = SMA(psy, m)
    return psy, psyma


def DPO(close, m1=20, m2=10, m3=6):
    """
    区间震荡线 (Detrended Price Oscillator)
    Returns: (dpo, madpo)
    """
    dpo = close - SMA(close, m1).shift(m2)
    madpo = SMA(dpo, m3)
    return dpo, madpo


# ==================== 波动率指标 ====================

def BBANDS(data, timeperiod=20, nbdevup=2, nbdevdn=2):
    """
    布林带 (Bollinger Bands)
    Returns: (upper, mid, lower)
    """
    mid = data.rolling(timeperiod).mean()
    std = data.rolling(timeperiod).std(ddof=0)
    upper = mid + std * nbdevup
    lower = mid - std * nbdevdn
    return upper, mid, lower


def TRANGE(high, low, close):
    """真实波幅 (True Range)"""
    hl = high - low
    hc = np.abs(high - close.shift())
    lc = np.abs(low - close.shift())
    return pd.concat([hl, hc, lc], axis=1).max(axis=1)


def ATR(high, low, close, timeperiod=14):
    """平均真实波幅 (Average True Range)"""
    tr = TRANGE(high, low, close)
    return tr.rolling(window=timeperiod).mean()


def NATR(high, low, close, timeperiod=14):
    """归一化平均真实波幅 (Normalized ATR), 百分比"""
    atr = ATR(high, low, close, timeperiod)
    return 100 * (atr / close)


def STDDEV(data, timeperiod=5, nbdev=1):
    """标准差"""
    return data.rolling(window=timeperiod).std(ddof=0) * nbdev


def TAQ(high, low, n=20):
    """
    唐安奇通道 (Donchian Channel)
    Returns: (upper, mid, lower)
    """
    upper = high.rolling(n).max()
    lower = low.rolling(n).min()
    mid = (upper + lower) / 2
    return upper, mid, lower


def EMV(high, low, volume, n=14, m=9):
    """
    简易波动指标 (Ease of Movement)
    Returns: (emv, maemv)
    """
    vol_ma = SMA(volume, n) / volume
    mid_move = 100 * (high + low - high.shift(1) - low.shift(1)) / (high + low)
    emv = SMA(mid_move * vol_ma * (high - low) / SMA(high - low, n), n)
    maemv = SMA(emv, m)
    return emv, maemv


# ==================== 量能指标 ====================

def OBV(close, volume):
    """能量潮 (On Balance Volume)"""
    direction = np.where(close > close.shift(1), volume,
                         np.where(close < close.shift(1), -volume, 0))
    return pd.Series(direction, index=close.index).cumsum()


def AD(high, low, close, volume):
    """
    累积/派发线 (Accumulation/Distribution Line)
    """
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.fillna(0)
    return (clv * volume).cumsum()


def ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10):
    """
    A/D 振荡指标 (Chaikin A/D Oscillator)
    """
    ad = AD(high, low, close, volume)
    return ad.ewm(span=fastperiod).mean() - ad.ewm(span=slowperiod).mean()


def MFI(high, low, close, volume, timeperiod=14):
    """
    资金流量指标 (Money Flow Index)
    >80 超买, <20 超卖
    """
    tp = (high + low + close) / 3
    mf = tp * volume
    tp_diff = tp.diff()
    pos_mf = pd.Series(np.where(tp_diff > 0, mf, 0), index=close.index).rolling(timeperiod).sum()
    neg_mf = pd.Series(np.where(tp_diff < 0, mf, 0), index=close.index).rolling(timeperiod).sum()
    mfi = 100 - (100 / (1 + pos_mf / neg_mf))
    return mfi


def VR(close, volume, m1=26):
    """
    成交量比率 (Volume Ratio)
    >100 多方主导, <100 空方主导
    """
    lc = close.shift(1)
    up_vol = pd.Series(np.where(close > lc, volume, 0), index=close.index).rolling(m1).sum()
    dn_vol = pd.Series(np.where(close <= lc, volume, 0), index=close.index).rolling(m1).sum()
    return up_vol / dn_vol * 100


# ==================== 情绪指标 ====================

def BRAR(open_, close, high, low, m1=26):
    """
    BRAR 情绪指标
    AR: 人气指标 (多空意愿)
    BR: 买卖意愿指标
    Returns: (ar, br)
    """
    ar = (high - open_).rolling(m1).sum() / (open_ - low).rolling(m1).sum() * 100
    br_up = pd.Series(np.maximum(0, high - close.shift(1)), index=close.index).rolling(m1).sum()
    br_dn = pd.Series(np.maximum(0, close.shift(1) - low), index=close.index).rolling(m1).sum()
    br = br_up / br_dn * 100
    return ar, br


# ==================== 辅助函数 ====================

def AVGPRICE(open_, high, low, close):
    """均价 (Average Price)"""
    return (open_ + high + low + close) / 4


def BETA(datax, datay, timeperiod=5):
    """Beta 系数"""
    cov = datax.rolling(window=timeperiod).cov(datay)
    var = datay.rolling(window=timeperiod).var()
    return cov / var


def MAX_VAL(data, timeperiod=14):
    """N期最高值"""
    return data.rolling(window=timeperiod).max()


def MIN_VAL(data, timeperiod=14):
    """N期最低值"""
    return data.rolling(window=timeperiod).min()


def SUM_VAL(data, timeperiod=14):
    """N期累计和"""
    return data.rolling(window=timeperiod).sum()


# ==================== 所有可用指标注册表 ====================

INDICATOR_REGISTRY = {
    # 趋势类
    'SMA':       {'func': SMA,       'params': ['close'],                    'desc': '简单移动平均线'},
    'EMA':       {'func': EMA,       'params': ['close'],                    'desc': '指数移动平均线'},
    'WMA':       {'func': WMA,       'params': ['close'],                    'desc': '加权移动平均线'},
    'MACD':      {'func': MACD,      'params': ['close'],                    'desc': 'MACD指标'},
    'ADX':       {'func': ADX,       'params': ['high', 'low', 'close'],     'desc': '平均趋向指标'},
    'DMI':       {'func': DMI,       'params': ['high', 'low', 'close'],     'desc': '动向指标'},
    'DMA':       {'func': DMA,       'params': ['close'],                    'desc': '平行线差指标'},
    'TRIX':      {'func': TRIX,      'params': ['close'],                    'desc': '三重指数平滑'},
    'BBI':       {'func': BBI,       'params': ['close'],                    'desc': '多空指标'},
    'LINEARREG': {'func': LINEARREG, 'params': ['close'],                    'desc': '线性回归'},
    # 震荡类
    'RSI':       {'func': RSI,       'params': ['close'],                    'desc': '相对强弱指数'},
    'KDJ':       {'func': KDJ,       'params': ['close', 'high', 'low'],     'desc': 'KDJ随机指标'},
    'STOCH':     {'func': STOCH,     'params': ['high', 'low', 'close'],     'desc': '随机振荡器'},
    'CCI':       {'func': CCI,       'params': ['high', 'low', 'close'],     'desc': '商品通道指数'},
    'WILLR':     {'func': WILLR,     'params': ['high', 'low', 'close'],     'desc': '威廉指标'},
    'WR':        {'func': WR,        'params': ['close', 'high', 'low'],     'desc': '威廉指标(通达信)'},
    'MOM':       {'func': MOM,       'params': ['close'],                    'desc': '动量指标'},
    'MTM':       {'func': MTM,       'params': ['close'],                    'desc': '动量指标(通达信)'},
    'ROC':       {'func': ROC,       'params': ['close'],                    'desc': '变动率'},
    'BIAS':      {'func': BIAS,      'params': ['close'],                    'desc': '乖离率'},
    'PSY':       {'func': PSY,       'params': ['close'],                    'desc': '心理线'},
    'DPO':       {'func': DPO,       'params': ['close'],                    'desc': '区间震荡线'},
    # 波动率类
    'BBANDS':    {'func': BBANDS,    'params': ['close'],                    'desc': '布林带'},
    'ATR':       {'func': ATR,       'params': ['high', 'low', 'close'],     'desc': '平均真实波幅'},
    'NATR':      {'func': NATR,      'params': ['high', 'low', 'close'],     'desc': '归一化ATR'},
    'TAQ':       {'func': TAQ,       'params': ['high', 'low'],              'desc': '唐安奇通道'},
    'EMV':       {'func': EMV,       'params': ['high', 'low', 'volume'],    'desc': '简易波动指标'},
    'STDDEV':    {'func': STDDEV,    'params': ['close'],                    'desc': '标准差'},
    # 量能类
    'OBV':       {'func': OBV,       'params': ['close', 'volume'],          'desc': '能量潮'},
    'AD':        {'func': AD,        'params': ['high', 'low', 'close', 'volume'], 'desc': '累积/派发线'},
    'ADOSC':     {'func': ADOSC,     'params': ['high', 'low', 'close', 'volume'], 'desc': 'A/D振荡指标'},
    'MFI':       {'func': MFI,       'params': ['high', 'low', 'close', 'volume'], 'desc': '资金流量指标'},
    'VR':        {'func': VR,        'params': ['close', 'volume'],          'desc': '成交量比率'},
    # 情绪类
    'BRAR':      {'func': BRAR,      'params': ['open', 'close', 'high', 'low'], 'desc': 'BRAR情绪指标'},
}

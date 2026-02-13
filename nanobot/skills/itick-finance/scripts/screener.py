"""
一夜持股法 选股策略脚本

使用方法 (通过 nanobot exec 调用):
    exec(command="python scripts/screener.py --token YOUR_TOKEN --region SH --codes 600519,601318,600036")

策略条件:
1. 时间：下午两点半开始筛选
2. 涨幅：3%-5%之间
3. 量比：量比大于1
4. 流通市值：50-200亿区间
5. 换手率：5%-10%之间
6. 成交量：成交量持续放大（最近3根K线）
7. 均线：呈多头向上发散形态 (MA5>MA10>MA20>MA60)
8. K线：股价位于均线上方
9. 分时图：股价全天高于分时均线(VWAP)，且走势强于大盘
10. 持仓：下午两点半入至第二天两点半出
"""
import json
import sys
import os
import math

# 将 scripts 目录加入路径以导入 indicators
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indicators import (
    calc_ma, calc_ema, calc_vwap, calc_macd, calc_rsi,
    calc_volume_ratio, check_volume_increasing,
    check_ma_bullish_alignment, check_price_above_mas,
    extract_ohlcv
)


def screen_stock(quote, klines_day, klines_1min, info, benchmark_chp=None):
    """
    对单只股票执行一夜持股法筛选。

    参数:
        quote: dict - 实时报价数据 (来自 /stock/quote)
        klines_day: list - 日K线数据 (至少60根, 来自 /stock/kline kType=8)
        klines_1min: list - 当日1分钟K线 (来自 /stock/kline kType=1)
        info: dict - 公司信息 (来自 /stock/info)
        benchmark_chp: float|None - 大盘涨跌幅，用于比较走势强弱

    返回:
        dict: {
            "pass": bool,          # 是否通过筛选
            "code": str,           # 股票代码
            "name": str,           # 股票名称
            "score": int,          # 满足条件数 (0-10)
            "details": dict,       # 每项条件的详细结果
            "summary": str         # 简要总结
        }
    """
    code = quote.get('s', '')
    name = info.get('n', code)
    details = {}
    score = 0

    # --- 条件1: 时间 (信息性，不作为硬性筛选) ---
    details["timing"] = {
        "desc": "下午两点半后筛选",
        "note": "策略要求14:30后入场，次日14:30前出场"
    }

    # --- 条件2: 涨幅 3%-5% ---
    chp = quote.get('chp', 0)
    in_range = 3.0 <= chp <= 5.0
    details["change_pct"] = {
        "value": chp,
        "target": "3%-5%",
        "pass": in_range
    }
    if in_range:
        score += 1

    # --- 条件3: 量比 > 1 ---
    if klines_day and len(klines_day) >= 6:
        volumes = [k['v'] for k in klines_day]
        avg_vol_5 = sum(volumes[-6:-1]) / 5
        current_vol = quote.get('v', 0)
        vol_ratio = round(current_vol / avg_vol_5, 2) if avg_vol_5 > 0 else 0
    else:
        vol_ratio = 0
    vr_pass = vol_ratio > 1.0
    details["volume_ratio"] = {
        "value": vol_ratio,
        "target": "> 1.0",
        "pass": vr_pass
    }
    if vr_pass:
        score += 1

    # --- 条件4: 流通市值 50-200亿 ---
    mcb = info.get('mcb', 0)
    mcb_billion = mcb / 1e8 if mcb else 0  # 转为亿
    mc_pass = 50 <= mcb_billion <= 200
    details["market_cap"] = {
        "value_billion": round(mcb_billion, 2),
        "target": "50-200亿",
        "pass": mc_pass
    }
    if mc_pass:
        score += 1

    # --- 条件5: 换手率 5%-10% ---
    tso = info.get('tso', 0)  # 总股本
    current_vol = quote.get('v', 0)
    turnover = round(current_vol / tso * 100, 2) if tso and tso > 0 else 0
    tr_pass = 5.0 <= turnover <= 10.0
    details["turnover_rate"] = {
        "value": turnover,
        "target": "5%-10%",
        "pass": tr_pass
    }
    if tr_pass:
        score += 1

    # --- 条件6: 成交量持续放大 ---
    if klines_day and len(klines_day) >= 3:
        day_volumes = [k['v'] for k in klines_day]
        vol_inc = check_volume_increasing(day_volumes, 3)
    else:
        vol_inc = False
    details["volume_increasing"] = {
        "value": vol_inc,
        "target": "最近3日成交量持续放大",
        "pass": vol_inc
    }
    if vol_inc:
        score += 1

    # --- 条件7: 均线多头排列 ---
    if klines_day and len(klines_day) >= 60:
        closes_day = [k['c'] for k in klines_day]
        bullish, ma_values = check_ma_bullish_alignment(closes_day, (5, 10, 20, 60))
    else:
        bullish = False
        ma_values = {}
    details["ma_bullish"] = {
        "value": bullish,
        "ma_values": ma_values,
        "target": "MA5>MA10>MA20>MA60",
        "pass": bullish
    }
    if bullish:
        score += 1

    # --- 条件8: 股价在均线上方 ---
    current_price = quote.get('ld', 0)
    if klines_day and len(klines_day) >= 20:
        closes_day = [k['c'] for k in klines_day]
        above_ma = check_price_above_mas(current_price, closes_day, (5, 10, 20))
    else:
        above_ma = False
    details["price_above_ma"] = {
        "value": above_ma,
        "current_price": current_price,
        "target": "股价 > MA5, MA10, MA20",
        "pass": above_ma
    }
    if above_ma:
        score += 1

    # --- 条件9: 股价高于分时均线(VWAP) ---
    if klines_1min and len(klines_1min) >= 10:
        min_closes = [k['c'] for k in klines_1min]
        min_volumes = [k['v'] for k in klines_1min]
        vwap = calc_vwap(min_closes, min_volumes)
        above_vwap = current_price > vwap[-1] if vwap else False
        vwap_value = round(vwap[-1], 2) if vwap else 0

        # 检查全天是否大部分时间在VWAP上方
        above_count = sum(1 for i in range(len(min_closes)) if min_closes[i] > vwap[i])
        above_ratio = round(above_count / len(min_closes) * 100, 1)
    else:
        above_vwap = False
        vwap_value = 0
        above_ratio = 0

    # 强于大盘判断
    stronger_than_bench = True
    if benchmark_chp is not None:
        stronger_than_bench = chp > benchmark_chp

    vwap_pass = above_vwap and above_ratio >= 60 and stronger_than_bench
    details["vwap_strength"] = {
        "above_vwap": above_vwap,
        "vwap_value": vwap_value,
        "above_vwap_ratio": f"{above_ratio}%",
        "stronger_than_benchmark": stronger_than_bench,
        "benchmark_chp": benchmark_chp,
        "target": "全天高于VWAP且强于大盘",
        "pass": vwap_pass
    }
    if vwap_pass:
        score += 1

    # --- 条件10: 持仓计划 (信息性) ---
    details["hold_plan"] = {
        "desc": "下午14:30买入，次日14:30前卖出",
        "note": "建议设置止损-3%，止盈目标根据量能判断"
    }

    # --- 综合结果 ---
    # 至少满足 7/9 个量化条件算通过 (去掉时间和持仓这2个非量化条件)
    passed = score >= 7

    if passed:
        summary = f"[强烈推荐] {name}({code}) 满足{score}/9项条件，符合一夜持股策略"
    elif score >= 5:
        summary = f"[关注] {name}({code}) 满足{score}/9项条件，部分符合策略"
    else:
        summary = f"[不符合] {name}({code}) 仅满足{score}/9项条件"

    return {
        "pass": passed,
        "code": code,
        "name": name,
        "score": score,
        "max_score": 9,
        "details": details,
        "summary": summary
    }


def format_result(result):
    """将筛选结果格式化为可读文本"""
    lines = []
    r = result
    d = r['details']

    emoji_pass = "OK"
    emoji_fail = "X"

    lines.append(f"## {r['name']} ({r['code']}) - 一夜持股法筛选")
    lines.append(f"综合评分: {r['score']}/{r['max_score']}")
    lines.append(f"结论: {r['summary']}")
    lines.append("")

    checks = [
        ("涨幅", "change_pct", lambda d: f"{d['value']}% (目标:{d['target']})"),
        ("量比", "volume_ratio", lambda d: f"{d['value']} (目标:{d['target']})"),
        ("流通市值", "market_cap", lambda d: f"{d['value_billion']}亿 (目标:{d['target']})"),
        ("换手率", "turnover_rate", lambda d: f"{d['value']}% (目标:{d['target']})"),
        ("量能放大", "volume_increasing", lambda d: f"{'是' if d['value'] else '否'} (目标:{d['target']})"),
        ("均线多头", "ma_bullish", lambda d: f"{'是' if d['value'] else '否'} {d.get('ma_values', '')}"),
        ("价在均线上", "price_above_ma", lambda d: f"{'是' if d['value'] else '否'} 当前价:{d['current_price']}"),
        ("VWAP强势", "vwap_strength", lambda d: f"{'是' if d['above_vwap'] else '否'} VWAP:{d['vwap_value']} 占比:{d['above_vwap_ratio']}"),
    ]

    for label, key, fmt_fn in checks:
        data = d.get(key, {})
        status = emoji_pass if data.get('pass') else emoji_fail
        lines.append(f"  [{status}] {label}: {fmt_fn(data)}")

    lines.append("")
    lines.append(f"操作建议: {d['hold_plan']['desc']}")
    lines.append(f"风控提示: {d['hold_plan']['note']}")

    return "\n".join(lines)


# ============ CLI 入口 ============

if __name__ == "__main__":
    # 用法示例: python screener.py '{"quote":{...},"klines_day":[...],"klines_1min":[...],"info":{...}}'
    # 或通过 nanobot exec 传入
    if len(sys.argv) > 1:
        try:
            data = json.loads(sys.argv[1])
            result = screen_stock(
                quote=data.get('quote', {}),
                klines_day=data.get('klines_day', []),
                klines_1min=data.get('klines_1min', []),
                info=data.get('info', {}),
                benchmark_chp=data.get('benchmark_chp')
            )
            print(format_result(result))
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
        except Exception as e:
            print(f"执行错误: {e}")
    else:
        print("用法: python screener.py '<JSON数据>'")
        print("JSON格式: {\"quote\":{}, \"klines_day\":[], \"klines_1min\":[], \"info\":{}, \"benchmark_chp\":0.5}")

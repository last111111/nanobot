#!/usr/bin/env python3
"""A股技术指标筛选工具 — 基于 Ashare + MyTT"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import numpy as np
import pandas as pd

# 把 Ashare-main 加入 path，复用已有库
ASHARE_DIR = str(Path(__file__).resolve().parent.parent / "Ashare-main")
sys.path.insert(0, ASHARE_DIR)

from Ashare import get_price  # noqa: E402
from MyTT import (  # noqa: E402
    MACD, KDJ, RSI, BOLL, DMI, CROSS, MA, EMA, ATR, CCI, WR,
    RET, HHV, LLV, REF,
)


# ── 1. 获取全市场 A 股代码 ───────────────────────────────────────────────

CACHE_FILE = Path(__file__).parent / ".stock_list_cache.json"
CACHE_TTL = 4 * 3600  # 4 小时缓存


def fetch_all_stocks() -> pd.DataFrame:
    """
    从新浪财经 API 获取全部 A 股股票列表（带本地缓存）。
    返回 DataFrame: code(sh600519格式), name, price, change_pct
    """
    # 检查缓存
    if CACHE_FILE.exists():
        cache_age = time.time() - CACHE_FILE.stat().st_mtime
        if cache_age < CACHE_TTL:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            print(f"使用缓存的股票列表（{len(cached)} 只，{cache_age/60:.0f} 分钟前）")
            return pd.DataFrame(cached)

    url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Referer": "http://finance.sina.com.cn",
    })

    all_items = []
    page = 1
    while True:
        params = {"page": page, "num": 100, "sort": "symbol", "asc": 1, "node": "hs_a"}
        for attempt in range(3):
            try:
                resp = session.get(url, params=params, timeout=15)
                items = resp.json()
                break
            except Exception:
                items = []
                if attempt == 2:
                    print(f"\n第 {page} 页请求失败，使用已获取数据")
                time.sleep(1 * (attempt + 1))
        if not items:
            break
        all_items.extend(items)
        print(f"\r  获取股票列表: 第 {page} 页, 累计 {len(all_items)} 只", end="", flush=True)
        page += 1
    session.close()
    print()

    if not all_items:
        raise RuntimeError("新浪 API 返回空数据")

    rows = []
    for item in all_items:
        symbol = item.get("symbol", "")  # 格式: sh600519 / sz000001 / bj920000
        name = item.get("name", "")
        price = item.get("trade", 0)
        change_pct = item.get("changepercent", 0)

        # 只保留沪深，排除北交所 (bj)
        if not symbol.startswith(("sh", "sz")):
            continue
        raw_code = symbol[2:]
        if symbol.startswith("sh") and not raw_code.startswith(("60", "68")):
            continue
        if symbol.startswith("sz") and not raw_code.startswith(("00", "30")):
            continue

        rows.append({
            "code": symbol,
            "name": name,
            "price": float(price) if price else 0,
            "change_pct": float(change_pct) if change_pct else 0,
        })

    df = pd.DataFrame(rows)
    print(f"获取到 {len(df)} 只沪深 A 股")

    # 写缓存
    CACHE_FILE.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    return df


# ── 2. 单只股票指标计算 ──────────────────────────────────────────────────

def calc_indicators(code: str, count: int = 120) -> dict | None:
    """
    获取单只股票日线数据并计算全部常用指标。
    返回 dict 或 None（获取失败时）。
    """
    try:
        df = get_price(code, frequency="1d", count=count)
        if df is None or len(df) < 30:
            return None

        CLOSE = df.close.values
        HIGH = df.high.values
        LOW = df.low.values
        OPEN = df.open.values
        VOL = df.volume.values

        # 指标计算
        dif, dea, macd_hist = MACD(CLOSE)
        k, d, j = KDJ(CLOSE, HIGH, LOW)
        rsi = RSI(CLOSE, N=14)

        # 金叉判断
        macd_golden = bool(CROSS(dif, dea)[-1]) if len(dif) > 1 else False
        kdj_golden = bool(CROSS(k, d)[-1]) if len(k) > 1 else False

        return {
            "code": code,
            "close": round(float(CLOSE[-1]), 2),
            "RSI": round(float(rsi[-1]), 2) if not np.isnan(rsi[-1]) else None,
            "MACD_DIF": round(float(dif[-1]), 4),
            "MACD_DEA": round(float(dea[-1]), 4),
            "MACD_HIST": round(float(macd_hist[-1]), 4),
            "KDJ_K": round(float(k[-1]), 2),
            "KDJ_D": round(float(d[-1]), 2),
            "KDJ_J": round(float(j[-1]), 2),
            "MACD_GOLDEN": macd_golden,
            "KDJ_GOLDEN": kdj_golden,
        }
    except Exception as e:
        return None


# ── 3. 批量扫描 ─────────────────────────────────────────────────────────

def scan_stocks(
    stocks: pd.DataFrame,
    max_workers: int = 10,
    count: int = 120,
) -> list[dict]:
    """并发扫描多只股票，返回指标结果列表。"""
    results = []
    total = len(stocks)
    done = 0
    failed = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(calc_indicators, row.code, count): row
            for row in stocks.itertuples()
        }

        for future in as_completed(futures):
            done += 1
            row = futures[future]
            result = future.result()

            if result:
                result["name"] = row.name  # 注意 itertuples 的 .name 是 index
                # 从 stocks df 里拿真实名字
                stock_row = stocks[stocks.code == result["code"]]
                if not stock_row.empty:
                    result["name"] = stock_row.iloc[0]["name"]
                results.append(result)
            else:
                failed += 1

            # 进度
            elapsed = time.time() - start_time
            speed = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / speed if speed > 0 else 0
            print(
                f"\r扫描进度: {done}/{total} "
                f"(成功 {len(results)}, 失败 {failed}) "
                f"速度 {speed:.1f} 只/秒, 预计剩余 {eta:.0f}秒",
                end="", flush=True,
            )

    print()  # 换行
    return results


# ── 4. 筛选策略 ─────────────────────────────────────────────────────────

def filter_oversold(results: list[dict]) -> list[dict]:
    """RSI < 30 超卖"""
    return [r for r in results if r.get("RSI") is not None and r["RSI"] < 30]


def filter_overbought(results: list[dict]) -> list[dict]:
    """RSI > 70 超买"""
    return [r for r in results if r.get("RSI") is not None and r["RSI"] > 70]


def filter_macd_golden(results: list[dict]) -> list[dict]:
    """MACD 金叉"""
    return [r for r in results if r.get("MACD_GOLDEN")]


def filter_kdj_golden(results: list[dict]) -> list[dict]:
    """KDJ 金叉"""
    return [r for r in results if r.get("KDJ_GOLDEN")]


def filter_custom(results: list[dict], expr: str) -> list[dict]:
    """
    自定义条件筛选，支持: RSI<30 AND KDJ_J<20
    可用字段: RSI, MACD_DIF, MACD_DEA, MACD_HIST, KDJ_K, KDJ_D, KDJ_J
    """
    filtered = []
    for r in results:
        try:
            # 构建安全的变量环境
            env = {k: v for k, v in r.items() if isinstance(v, (int, float)) and v is not None}
            # 替换 AND/OR 为 Python 语法
            py_expr = expr.replace(" AND ", " and ").replace(" OR ", " or ")
            if eval(py_expr, {"__builtins__": {}}, env):  # noqa: S307
                filtered.append(r)
        except Exception:
            continue
    return filtered


# ── 5. 输出 ─────────────────────────────────────────────────────────────

def print_results(results: list[dict], sort_by: str = "RSI", title: str = ""):
    """格式化输出筛选结果。"""
    if not results:
        print("未找到符合条件的股票。")
        return

    # 排序
    results.sort(key=lambda r: r.get(sort_by, 999) if r.get(sort_by) is not None else 999)

    print(f"\n{'='*80}")
    if title:
        print(f"  {title}")
        print(f"{'='*80}")
    print(f"{'代码':<12} {'名称':<10} {'收盘价':>8} {'RSI':>8} {'KDJ_K':>8} {'KDJ_J':>8} {'MACD_DIF':>10}")
    print(f"{'-'*80}")

    for r in results:
        print(
            f"{r['code']:<12} {r.get('name', ''):.<10} "
            f"{r['close']:>8.2f} "
            f"{r.get('RSI', 0):>8.2f} "
            f"{r.get('KDJ_K', 0):>8.2f} "
            f"{r.get('KDJ_J', 0):>8.2f} "
            f"{r.get('MACD_DIF', 0):>10.4f}"
        )

    print(f"{'-'*80}")
    print(f"共 {len(results)} 只股票")


# ── 主程序 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="A股技术指标筛选工具")
    parser.add_argument("--oversold", action="store_true", help="筛选 RSI < 30 超卖股")
    parser.add_argument("--overbought", action="store_true", help="筛选 RSI > 70 超买股")
    parser.add_argument("--macd-golden", action="store_true", help="筛选 MACD 金叉")
    parser.add_argument("--kdj-golden", action="store_true", help="筛选 KDJ 金叉")
    parser.add_argument("--custom", type=str, help='自定义条件，如 "RSI<25 AND KDJ_J<20"')
    parser.add_argument("--limit", type=int, default=0, help="限制扫描股票数量（0=全部）")
    parser.add_argument("--workers", type=int, default=10, help="并发数（默认10）")
    parser.add_argument("--include-st", action="store_true", help="包含 ST 股票")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    # 如果没有指定任何筛选条件，默认找超卖
    if not (args.oversold or args.overbought or args.macd_golden or args.kdj_golden or args.custom):
        args.oversold = True
        print("未指定筛选条件，默认使用 --oversold (RSI < 30)")

    # 1. 获取股票列表
    print("正在获取 A 股列表...")
    stocks = fetch_all_stocks()

    # 排除 ST
    if not args.include_st:
        before = len(stocks)
        stocks = stocks[~stocks["name"].str.contains("ST", case=False, na=False)]
        excluded = before - len(stocks)
        if excluded:
            print(f"已排除 {excluded} 只 ST 股票，剩余 {len(stocks)} 只")

    # 限制数量
    if args.limit > 0:
        stocks = stocks.head(args.limit)
        print(f"限制扫描前 {args.limit} 只")

    # 2. 批量扫描
    print(f"开始扫描 {len(stocks)} 只股票（并发 {args.workers}）...")
    results = scan_stocks(stocks, max_workers=args.workers)
    print(f"扫描完成，成功获取 {len(results)} 只股票数据")

    # 3. 应用筛选
    filtered = results
    title_parts = []

    if args.oversold:
        filtered = filter_oversold(filtered)
        title_parts.append("RSI 超卖 (< 30)")
    if args.overbought:
        filtered = filter_overbought(filtered)
        title_parts.append("RSI 超买 (> 70)")
    if args.macd_golden:
        filtered = filter_macd_golden(filtered)
        title_parts.append("MACD 金叉")
    if args.kdj_golden:
        filtered = filter_kdj_golden(filtered)
        title_parts.append("KDJ 金叉")
    if args.custom:
        filtered = filter_custom(filtered, args.custom)
        title_parts.append(f"自定义: {args.custom}")

    # 4. 输出
    title = " + ".join(title_parts)

    if args.json:
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
    else:
        sort_key = "RSI" if (args.oversold or args.overbought) else "MACD_DIF"
        print_results(filtered, sort_by=sort_key, title=title)


if __name__ == "__main__":
    main()

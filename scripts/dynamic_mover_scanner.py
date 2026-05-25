"""动态 AI 异动发现。

交易日尝试用 Yahoo quote 接口抓取价格和成交量；失败时回退到新闻信号。
非交易日则输出最近值得关注的新 AI 主线公司。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


AI_MOVER_CANDIDATES = [
    "NVDA", "AMD", "AVGO", "QCOM", "AMBA", "TSM", "ANET", "VRT", "GEV", "VST", "CEG",
    "AAPL", "MSFT", "TSLA", "MRVL", "SMCI", "DELL", "ARM", "MU", "PLTR", "SNOW",
]


@dataclass
class DynamicMover:
    """动态异动或新增主线公司。"""

    ticker: str
    reason: str
    move_type: str
    price_change_pct: float | None = None
    volume_note: str = "需要继续验证"


def fetch_yahoo_quotes(tickers: list[str]) -> list[dict[str, Any]]:
    """抓取 Yahoo Finance quote 数据，失败返回空列表。"""

    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    try:
        response = requests.get(
            url,
            params={"symbols": ",".join(tickers)},
            timeout=12,
            headers={"User-Agent": "ai-market-brief-cn/1.0"},
        )
        response.raise_for_status()
        return response.json().get("quoteResponse", {}).get("result", [])
    except (requests.RequestException, ValueError) as exc:
        print(f"[WARN] Yahoo quote 抓取失败: {exc}")
        return []


def classify_move(change_pct: float | None, reason: str) -> str:
    """把异动分为炒作、板块联动或长期叙事变化。"""

    text = reason.lower()
    if any(word in text for word in ["earnings", "guidance", "order", "revenue", "contract"]):
        return "long-term narrative shift（长期叙事变化）"
    if change_pct is not None and abs(change_pct) >= 8:
        return "meme/speculation（炒作或高波动交易）"
    return "sector-wide move（板块联动）"


def scan_dynamic_movers(news: list[Any], market_mode: Any) -> list[DynamicMover]:
    """扫描动态 AI movers。"""

    if market_mode.is_trading_day:
        quotes = fetch_yahoo_quotes(AI_MOVER_CANDIDATES)
        movers: list[DynamicMover] = []
        for quote in quotes:
            ticker = quote.get("symbol", "")
            change_pct = quote.get("regularMarketChangePercent")
            volume = quote.get("regularMarketVolume")
            avg_volume = quote.get("averageDailyVolume3Month")
            if change_pct is None:
                continue
            if abs(change_pct) >= 3 or (volume and avg_volume and volume > avg_volume * 1.5):
                reason = "价格或成交量显著偏离近期均值，需结合新闻、财报和板块资金流验证。"
                movers.append(
                    DynamicMover(
                        ticker=ticker,
                        reason=reason,
                        move_type=classify_move(change_pct, reason),
                        price_change_pct=round(float(change_pct), 2),
                        volume_note="成交量高于均值" if volume and avg_volume and volume > avg_volume * 1.5 else "成交量需继续验证",
                    )
                )
        if movers:
            return sorted(movers, key=lambda item: abs(item.price_change_pct or 0), reverse=True)[:6]

    return scan_news_driven_companies(news, market_mode)


def scan_news_driven_companies(news: list[Any], market_mode: Any) -> list[DynamicMover]:
    """用新闻标题发现新进入 AI 主线的公司。"""

    movers: list[DynamicMover] = []
    for ticker in AI_MOVER_CANDIDATES:
        related = [
            item.title
            for item in news
            if ticker.lower() in f"{item.title} {item.summary} {item.query}".lower()
        ]
        if related:
            label = "最近值得关注的新进入 AI 主线公司" if not market_mode.is_trading_day else "新闻驱动异动候选"
            movers.append(
                DynamicMover(
                    ticker=ticker,
                    reason=related[0],
                    move_type=label,
                    volume_note="非交易日不判断成交量" if not market_mode.is_trading_day else "需要行情验证",
                )
            )
    return movers[:6]

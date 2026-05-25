"""免费新闻来源抓取。

优先使用 RSS，因为它稳定、免费、容易调试。抓取失败时只返回空列表，
不会让整个日报生成流程中断。
"""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from html import unescape
import re
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import requests


REQUEST_TIMEOUT = 12


@dataclass
class NewsItem:
    """统一的新闻条目格式。"""

    title: str
    source: str
    link: str
    summary: str = ""
    published: str = ""
    query: str = ""


def clean_text(text: str) -> str:
    """清理 RSS 摘要里的 HTML 标签和多余空白。"""

    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_published(entry: object) -> str:
    """把 RSS 时间转成 YYYY-MM-DD，失败则返回空字符串。"""

    raw = getattr(entry, "published", "") or getattr(entry, "updated", "")
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        return ""


def fetch_rss(url: str, source_name: str, query: str = "", limit: int = 10) -> list[NewsItem]:
    """抓取一个 RSS 地址。"""

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "ai-market-brief-cn/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[WARN] 抓取失败: {source_name} {url} - {exc}")
        return []

    feed = feedparser.parse(response.content)
    items: list[NewsItem] = []
    for entry in feed.entries[:limit]:
        items.append(
            NewsItem(
                title=clean_text(getattr(entry, "title", "")),
                source=source_name,
                link=getattr(entry, "link", ""),
                summary=clean_text(getattr(entry, "summary", "")),
                published=parse_published(entry),
                query=query,
            )
        )
    return [item for item in items if item.title and item.link]


def google_news_rss(query: str) -> str:
    """生成 Google News RSS 搜索地址。"""

    encoded = quote_plus(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"


def yahoo_finance_rss(ticker: str) -> str:
    """生成 Yahoo Finance 单股票 RSS 地址。"""

    return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


def dedupe_news(items: Iterable[NewsItem], limit: int = 30) -> list[NewsItem]:
    """按链接和标题去重。"""

    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.link or item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def fetch_market_news(watchlist: list[dict[str, str]]) -> list[NewsItem]:
    """抓取市场主题新闻和重点公司新闻。"""

    topic_queries = [
        "AI semiconductor data center chips",
        "edge AI robotics semiconductor",
        "AI data center power grid electricity",
        "robotics physical AI Nvidia Qualcomm Ambarella",
    ]
    all_items: list[NewsItem] = []

    for query in topic_queries:
        all_items.extend(fetch_rss(google_news_rss(query), "Google News RSS", query=query, limit=8))

    for company in watchlist:
        ticker = company["ticker"]
        all_items.extend(fetch_rss(yahoo_finance_rss(ticker), "Yahoo Finance RSS", query=ticker, limit=4))

    return dedupe_news(all_items, limit=60)


def company_reference_links(ticker: str) -> list[dict[str, str]]:
    """提供公司研究时常用的免费参考链接。"""

    return [
        {
            "name": "SEC filings",
            "url": f"https://www.sec.gov/edgar/search/#/q={ticker}",
        },
        {
            "name": "Yahoo Finance",
            "url": f"https://finance.yahoo.com/quote/{ticker}",
        },
        {
            "name": "Google News",
            "url": f"https://news.google.com/search?q={quote_plus(ticker)}",
        },
    ]

"""生成中文 AI 市场每日简报。

运行方式：
    python scripts/daily_brief.py

脚本会抓取免费 RSS 新闻，读取 watchlist，选择当天研究公司，
并在 reports/ 目录输出 Markdown 文件。
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv

from company_rotation import pick_company_for_date
from llm_summary import compact_news_for_prompt, summarize_with_openai
from sources import NewsItem, company_reference_links, fetch_market_news


ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT / "data" / "company_watchlist.json"
REPORTS_DIR = ROOT / "reports"

FOCUS_TICKERS = ["NVDA", "QCOM", "AMBA", "AMD", "AVGO", "TSM", "VRT", "GEV", "VST"]

COMPANY_ALIASES = {
    "NVDA": ["nvidia", "英伟达"],
    "QCOM": ["qualcomm", "snapdragon", "高通"],
    "AMBA": ["ambarella"],
    "AMD": ["advanced micro devices", "amd"],
    "AVGO": ["broadcom", "博通"],
    "TSM": ["taiwan semiconductor", "tsmc", "台积电"],
    "ANET": ["arista"],
    "VRT": ["vertiv"],
    "GEV": ["ge vernova"],
    "VST": ["vistra"],
    "CEG": ["constellation energy"],
    "AAPL": ["apple", "苹果"],
    "MSFT": ["microsoft", "微软"],
    "TSLA": ["tesla", "特斯拉"],
}


def load_watchlist() -> list[dict[str, Any]]:
    """读取公司观察列表。"""

    with WATCHLIST_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_company(companies: list[dict[str, Any]], ticker: str) -> dict[str, Any] | None:
    """按 ticker 查找公司。"""

    return next((company for company in companies if company["ticker"] == ticker), None)


def related_companies(item: NewsItem, companies: list[dict[str, Any]]) -> list[str]:
    """根据标题和摘要粗略匹配受影响公司。"""

    text = f"{item.title} {item.summary}".lower()
    matched: list[str] = []
    for company in companies:
        ticker = company["ticker"]
        chinese_name = company.get("中文名", "")
        aliases = COMPANY_ALIASES.get(ticker, [])
        if ticker.lower() in text or chinese_name.lower() in text or any(alias in text for alias in aliases):
            matched.append(ticker)
    return matched[:6]


def select_top_news(news: list[NewsItem], companies: list[dict[str, Any]], limit: int = 8) -> list[NewsItem]:
    """选择最适合日报展示的新闻。

    简单策略：优先保留能匹配 watchlist 或核心主题的新闻。
    """

    keywords = [
        "ai",
        "artificial intelligence",
        "semiconductor",
        "chip",
        "data center",
        "robot",
        "power",
        "electricity",
        "nuclear",
        "edge",
    ]
    scored: list[tuple[int, NewsItem]] = []
    for item in news:
        text = f"{item.title} {item.summary} {item.query}".lower()
        score = sum(1 for keyword in keywords if keyword in text)
        score += len(related_companies(item, companies)) * 2
        scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def build_llm_prompt(
    today: date,
    companies: list[dict[str, Any]],
    news: list[NewsItem],
    research_company: dict[str, Any],
) -> str:
    """构造 LLM 提示词。"""

    watchlist_text = "\n".join(
        f"- {c['ticker']} {c['中文名']}：{c['所属主题']}；观察逻辑：{c['核心观察逻辑']}"
        for c in companies
    )
    return f"""
请基于下面的 watchlist 和新闻，生成一份中文 Markdown 日报。

日期：{today.isoformat()}

必须严格使用以下结构：
# AI 市场每日简报 - {today.isoformat()}

## 1. 今日核心结论
5 条 bullet。

## 2. 今日 AI / 半导体 / Edge AI 新闻
5-10 条，每条包括：标题、来源、链接、为什么重要、影响哪些公司。

## 3. 重点股票观察
覆盖 NVDA、QCOM、AMBA、AMD、AVGO、TSM、VRT、GEV、VST。
每家公司包括：今日异动、可能原因、是否影响长期逻辑。
如果没有足够价格或新闻信息，请明确写“需要继续验证”，不要编造股价。

## 4. 今日公司商业逻辑研究
公司：{research_company['ticker']} {research_company['中文名']}
必须包含固定小节：一句话理解、收入来源、增长故事、护城河、估值问题、风险、未来需要观察的验证点、我的初步判断。

## 5. 今日需要继续思考的问题
3 个问题。

Watchlist：
{watchlist_text}

新闻：
{compact_news_for_prompt(news)}
""".strip()


def fallback_core_conclusions(top_news: list[NewsItem]) -> str:
    """无 LLM 时生成基础核心结论。"""

    bullets = [
        "AI 基础设施仍是观察主线：芯片、网络、电力、散热和数据中心资本开支需要一起跟踪。",
        "端侧 AI 与 Edge AI 的投资逻辑需要看真实产品周期，而不是只看概念发布。",
        "电力和核电公司与 AI 数据中心需求的关系正在变强，但需要验证长期合同和电价假设。",
        "机器人和 Physical AI 仍偏中长期，短期重点看客户合作、设计导入和真实部署。",
        "今天抓取的新闻适合做线索池，具体结论仍需要结合财报、指引和股价异动继续验证。",
    ]
    if top_news:
        bullets[0] = f"今日新闻线索中最值得先读的是：{top_news[0].title}"
    return "\n".join(f"- {bullet}" for bullet in bullets)


def fallback_news_section(top_news: list[NewsItem], companies: list[dict[str, Any]]) -> str:
    """无 LLM 时生成新闻区。"""

    if not top_news:
        return "- 今天 RSS 抓取没有返回可用新闻。建议检查网络、RSS 源或稍后重试。"

    lines: list[str] = []
    for item in top_news:
        affected = related_companies(item, companies)
        lines.append(
            f"- **标题**：{item.title}\n"
            f"  - 来源：{item.source}\n"
            f"  - 链接：{item.link}\n"
            f"  - 为什么重要：这条新闻可能影响 AI、半导体、数据中心、电力或机器人产业链预期，"
            f"需要进一步阅读原文确认具体影响。\n"
            f"  - 影响哪些公司：{', '.join(affected) if affected else '暂未直接匹配 watchlist，公司影响需要继续验证'}"
        )
    return "\n\n".join(lines)


def fallback_stock_watch(companies: list[dict[str, Any]], news: list[NewsItem]) -> str:
    """无 LLM 时生成重点股票观察。"""

    sections: list[str] = []
    for ticker in FOCUS_TICKERS:
        company = find_company(companies, ticker)
        if not company:
            continue
        aliases = COMPANY_ALIASES.get(ticker, [])
        company_news = [
            item
            for item in news
            if ticker in related_companies(item, companies)
            or item.query == ticker
            or any(alias in f"{item.title} {item.summary}".lower() for alias in aliases)
        ]
        headline = company_news[0].title if company_news else "暂无直接匹配新闻"
        sections.append(
            f"### {ticker} - {company['中文名']}\n\n"
            f"- 今日异动：脚本未接入实时行情，股价异动需要到行情软件继续验证。\n"
            f"- 可能原因：{headline}。\n"
            f"- 是否影响长期逻辑：当前只能作为跟踪线索；长期逻辑仍看：{company['核心观察逻辑']}"
        )
    return "\n\n".join(sections)


def fallback_company_research(company: dict[str, Any]) -> str:
    """无 LLM 时生成公司商业逻辑研究模板。"""

    links = company_reference_links(company["ticker"])
    link_text = "\n".join(f"- {link['name']}：{link['url']}" for link in links)
    return f"""### 公司：{company['ticker']} - {company['中文名']}

#### 一句话理解
{company['中文名']}的核心跟踪主题是：{company['所属主题']}。需要理解它如何把这个主题转化为收入、利润和现金流。

#### 收入来源
请优先阅读最新 10-K / 10-Q、财报电话会和 Investor Relations 材料，拆分主要业务分部和客户结构。

#### 增长故事
当前初步观察逻辑：{company['核心观察逻辑']}

#### 护城河
需要继续验证技术壁垒、客户粘性、供应链能力、规模优势和生态位置。

#### 估值问题
市场可能已经计入部分成长预期。需要比较收入增长、利润率、自由现金流和估值倍数是否匹配。

#### 风险
- 需求低于预期，导致收入或订单增长放缓。
- 竞争加剧，价格、份额或利润率承压。
- 客户集中或单一产品周期导致业绩波动。
- 资本开支、供应链或监管变化影响交付。
- 估值过高时，轻微低于预期也可能带来较大股价波动。

#### 未来需要观察的验证点
- revenue growth 是否持续。
- guidance 是否上修或下修。
- gross margin / operating margin 是否稳定。
- design wins、客户合作和真实部署是否增加。
- 订单、积压订单或长期合同是否支持增长故事。

#### 我的初步判断
这家公司值得跟踪，但今天的基础模板不能替代深入研究。下一步应阅读财报和管理层指引，确认增长故事是否已经体现在真实数字里。

参考链接：
{link_text}"""


def build_fallback_report(
    today: date,
    companies: list[dict[str, Any]],
    news: list[NewsItem],
    research_company: dict[str, Any],
) -> str:
    """没有 OpenAI 输出时，生成完整基础日报。"""

    top_news = select_top_news(news, companies, limit=8)
    return f"""# AI 市场每日简报 - {today.isoformat()}

## 1. 今日核心结论
{fallback_core_conclusions(top_news)}

## 2. 今日 AI / 半导体 / Edge AI 新闻
{fallback_news_section(top_news, companies)}

## 3. 重点股票观察
{fallback_stock_watch(companies, news)}

## 4. 今日公司商业逻辑研究
{fallback_company_research(research_company)}

## 5. 今日需要继续思考的问题
- 今天哪些新闻只是短期情绪，哪些会真正改变公司未来 2-3 年收入和利润？
- AI 数据中心需求会先体现在哪些环节：GPU、网络、散热、电力、核电还是软件？
- 对今天轮换研究的公司，下一份财报最应该验证哪 3 个数字？
"""


def write_report(content: str, today: date) -> Path:
    """写入 Markdown 报告。"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{today.isoformat()}-ai-market-brief-cn.md"
    report_path.write_text(content.strip() + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    """主流程入口。"""

    load_dotenv(ROOT / ".env")
    today = date.today()

    try:
        companies = load_watchlist()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] 无法读取 watchlist: {exc}")
        return 1

    research_company = pick_company_for_date(companies, today)
    news = fetch_market_news(companies)

    prompt = build_llm_prompt(today, companies, news, research_company)
    llm_report = summarize_with_openai(prompt)
    content = llm_report or build_fallback_report(today, companies, news, research_company)

    report_path = write_report(content, today)
    print(f"[OK] 已生成报告: {report_path}")
    if not llm_report:
        print("[INFO] 未使用 OpenAI，总结为基础模板。配置 OPENAI_API_KEY 后可生成更完整中文分析。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

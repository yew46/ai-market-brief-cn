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
from dynamic_mover_scanner import DynamicMover, scan_dynamic_movers
from llm_summary import compact_news_for_prompt, summarize_with_openai
from market_calendar import MarketMode, get_market_mode
from narrative_detection import NarrativeShift, detect_narrative_shifts, infer_primary_narrative
from rerating_analysis import ReratingProfile, build_rerating_profile
from sector_relationship_engine import build_relationship_chain, format_relationship_chain
from sources import NewsItem, company_reference_links, enrich_article_text, fetch_market_news
from theme_clustering import ThemeSignal, build_theme_heatmap, theme_summary
from thesis_tracker import Thesis, build_thesis_table


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


def select_top_news(news: list[NewsItem], companies: list[dict[str, Any]], limit: int = 1) -> list[NewsItem]:
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
    featured_news: list[NewsItem],
    research_company: dict[str, Any],
    market_mode: MarketMode,
    primary_narrative: str,
    theme_signals: list[ThemeSignal],
    narrative_shifts: list[NarrativeShift],
    movers: list[DynamicMover],
    rerating_profile: ReratingProfile,
    relationship_chain: list[str],
    theses: list[Thesis],
) -> str:
    """构造 LLM 提示词。"""

    watchlist_text = "\n".join(
        f"- {c['ticker']} {c['中文名']}：{c['所属主题']}；观察逻辑：{c['核心观察逻辑']}"
        for c in companies
    )
    featured_text = compact_news_for_prompt(featured_news, limit=1)
    theme_text = format_theme_signals(theme_signals)
    shift_text = format_narrative_shifts(narrative_shifts)
    mover_text = format_movers(movers)
    thesis_text = format_thesis_table(theses)
    moat_text = "\n".join(f"- {key}: {value}" for key, value in rerating_profile.moat_analysis.items())
    return f"""
请基于下面的信息，生成一份中文 Markdown 报告。
报告定位：AI Theme Intelligence System（AI 主题趋势研究系统）。
风格：专业、分析型、类似科技 hedge fund research note，但适合强学习型初学者阅读。
不要只做新闻翻译，必须输出结构化判断。信息不足时明确写“需要继续验证”。

日期：{today.isoformat()}
报告模式：{market_mode.mode_name}
模式原因：{market_mode.reason}

必须严格使用以下结构：
# AI Theme Intelligence System - {today.isoformat()}

## 0. 报告模式
写明 Trading Day Mode 或 Non-Trading Day / Weekend Research Mode，并解释今天为什么采用该模式。

## 1. 今日市场主线
如果是交易日，回答“市场今天真正交易的是什么？”
如果是非交易日，回答“最近市场 / 产业最重要的 AI 主线是什么？”
必须把主线和可验证证据连接起来。

## 2. Narrative Shift（叙事迁移）
解释是否发生 training -> inference、GPU -> networking、cloud AI -> edge AI、chatbot -> physical AI、AI model -> AI infrastructure、datacenter -> power/cooling bottleneck 等迁移。
必须解释：为什么重要、哪些公司受益、哪些环节可能失去定价权、这是短期交易还是长期产业趋势。

## 3. AI Sector Heatmap（AI 板块热度图）
覆盖 GPU、Networking、Edge AI、Robotics、AI software、Power、Cooling、Foundry、AI PC、Datacenter、Inference、Physical AI。
必须输出：当前最热主题、正在减弱的主题、新出现的主题、需要继续验证的主题。

## 4. Dynamic AI Movers（动态 AI 异动发现）
交易日：解释 AI 异常异动、高成交量、earnings reaction、market narrative shift。
非交易日：改成“最近值得关注的新进入 AI 主线公司”，重点看新订单、新产品、新合作、earnings call narrative、产业链位置。
每个对象都要分类：meme/speculation、sector-wide move、long-term narrative shift，或非交易日主线候选。

## 5. 深度公司研究
公司：{research_company['ticker']} {research_company['中文名']}
必须包含：当前市场认知、Bull Case、Bear Case、Real Rerating Trigger、Moat Analysis、Price-In Status、关键观察指标、我的初步判断。

## 6. AI Industry Chain Mapping（AI 产业链关系图）
解释 AI 不同板块之间的因果关系，帮助建立产业结构理解能力。

## 7. Thesis Tracking（长期 thesis 跟踪）
用 Markdown 表格输出：Thesis、当前状态、证据、需要验证。

## 8. Thinking Questions（思考问题）
输出 5 个更深的问题，例如：什么还没有 fully priced in？哪一层真正赚最多利润？谁控制 ecosystem？这是短期交易还是长期迁移？

Watchlist：
{watchlist_text}

系统初步判断：
- 主线：{primary_narrative}
- 主题热度：
{theme_text}
- 叙事迁移：
{shift_text}
- 动态异动 / 新主线候选：
{mover_text}
- 产业链关系：
{format_relationship_chain(relationship_chain)}
- 深度研究公司初稿：
  - 当前市场认知：{rerating_profile.market_perception}
  - Bull Case：{rerating_profile.bull_case}
  - Bear Case：{rerating_profile.bear_case}
  - Real Rerating Trigger：{rerating_profile.rerating_trigger}
  - Price-In Status：{rerating_profile.price_in_status}
  - Moat Analysis：
{moat_text}
  - 关键观察指标：{', '.join(rerating_profile.key_metrics)}
- Thesis Tracking：
{thesis_text}

精选新闻正文：
{featured_text}

其他新闻线索：
{compact_news_for_prompt(news)}
""".strip()


def format_theme_signals(signals: list[ThemeSignal]) -> str:
    """把主题热度转成提示词和 fallback 可读文本。"""

    if not signals:
        return "- 暂无主题信号。"
    lines = []
    for signal in signals[:12]:
        evidence = "；".join(signal.evidence[:2]) if signal.evidence else "暂无直接新闻证据"
        lines.append(f"- {signal.theme}: score={signal.score}; evidence={evidence}")
    return "\n".join(lines)


def format_narrative_shifts(shifts: list[NarrativeShift]) -> str:
    """格式化叙事迁移。"""

    if not shifts:
        return "- 暂未识别到明确叙事迁移，需要继续验证。"
    lines = []
    for shift in shifts:
        lines.append(
            f"- {shift.name}: {shift.importance} 受益：{', '.join(shift.beneficiaries) or '待验证'}；"
            f"可能失去定价权：{', '.join(shift.potential_losers) or '待验证'}；性质：{shift.duration}"
        )
    return "\n".join(lines)


def format_movers(movers: list[DynamicMover]) -> str:
    """格式化动态异动。"""

    if not movers:
        return "- 暂未发现明确动态异动或新主线公司。"
    lines = []
    for mover in movers:
        pct = f"{mover.price_change_pct}%" if mover.price_change_pct is not None else "非交易日不适用"
        lines.append(
            f"- {mover.ticker}: 价格变化={pct}; 原因={mover.reason}; 分类={mover.move_type}; 成交量={mover.volume_note}"
        )
    return "\n".join(lines)


def format_thesis_table(theses: list[Thesis]) -> str:
    """格式化 thesis tracking 表格。"""

    rows = ["| Thesis | 当前状态 | 证据 | 需要验证 |", "|---|---|---|---|"]
    for thesis in theses:
        rows.append(f"| {thesis.name} | {thesis.status} | {thesis.evidence} | {thesis.needs_validation} |")
    return "\n".join(rows)


def fallback_market_mode_section(market_mode: MarketMode) -> str:
    """无 LLM 时输出报告模式。"""

    return f"- 报告模式：{market_mode.mode_name}\n- 判断原因：{market_mode.reason}"


def fallback_main_line(primary_narrative: str, market_mode: MarketMode) -> str:
    """无 LLM 时输出市场主线。"""

    if market_mode.is_trading_day:
        return (
            f"{primary_narrative}\n\n"
            "交易日要继续验证：这条主线是否同时体现在股价、成交量、领涨/领跌公司和 earnings reaction 中。"
        )
    return (
        f"{primary_narrative}\n\n"
        "非交易日不应强行写股价异动，更适合检查产业证据、管理层表态、订单和长期 thesis 是否变强。"
    )


def fallback_heatmap_section(signals: list[ThemeSignal]) -> str:
    """无 LLM 时输出 AI sector heatmap。"""

    summary = theme_summary(signals)

    def names(items: list[ThemeSignal]) -> str:
        return ", ".join(f"{item.theme}({item.score})" for item in items) or "暂无"

    return (
        f"- 当前最热主题：{names(summary['hot'])}\n"
        f"- 新出现 / 次热主题：{names(summary['emerging'])}\n"
        f"- 正在减弱的主题：{names(summary['weakening'])}\n"
        f"- 需要继续验证：{names(summary['needs_validation'])}\n\n"
        f"详细信号：\n{format_theme_signals(signals)}"
    )


def fallback_company_research_v2(company: dict[str, Any], profile: ReratingProfile) -> str:
    """无 LLM 时输出升级版公司研究。"""

    moat = "\n".join(f"- {key}: {value}" for key, value in profile.moat_analysis.items())
    metrics = "\n".join(f"- {metric}" for metric in profile.key_metrics)
    return f"""### 公司：{company['ticker']} - {company['中文名']}

#### 当前市场认知
{profile.market_perception}

#### Bull Case（看多逻辑）
{profile.bull_case}

#### Bear Case（看空逻辑）
{profile.bear_case}

#### Real Rerating Trigger
{profile.rerating_trigger}

#### 护城河分析（Moat Analysis）
{moat}

#### Price-In Status
{profile.price_in_status}。这是启发式判断，需要结合估值倍数、业绩指引和市场预期继续验证。

#### 关键观察指标
{metrics}

#### 我的初步判断
{company['中文名']}不是只看一条新闻就能判断的公司。关键是判断它到底只是趋势受益者，还是能在产业链中持续捕获利润的价值捕获者。"""


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

    item = top_news[0]
    affected = related_companies(item, companies)
    source_text = item.article_text or item.summary or "正文抓取不足，需要继续读原文验证。"
    short_summary = source_text[:600]
    return (
        f"### 新闻：{item.title}\n\n"
        f"- 来源：{item.source}\n"
        f"- 链接：[原文链接]({item.link})\n"
        f"- 中文内容摘要：{short_summary}\n"
        f"- 为什么重要：这条新闻可能影响 AI、半导体、数据中心、电力或机器人产业链预期，"
        f"需要进一步阅读原文确认具体影响。\n"
        f"- 影响哪些公司：{', '.join(affected) if affected else '暂未直接匹配 watchlist，公司影响需要继续验证'}\n"
        f"- 需要继续验证：查看原文细节、相关公司财报指引、订单或客户合作是否支持这条新闻的长期影响。"
    )


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
    featured_news: list[NewsItem],
    research_company: dict[str, Any],
    market_mode: MarketMode,
    primary_narrative: str,
    theme_signals: list[ThemeSignal],
    narrative_shifts: list[NarrativeShift],
    movers: list[DynamicMover],
    rerating_profile: ReratingProfile,
    relationship_chain: list[str],
    theses: list[Thesis],
) -> str:
    """没有 OpenAI 输出时，生成 AI Theme Intelligence 基础报告。"""

    top_news = featured_news or select_top_news(news, companies, limit=1)
    mode_label = "交易日模式" if market_mode.is_trading_day else "非交易日研究模式"
    dynamic_title = "Dynamic AI Movers（动态 AI 异动发现）" if market_mode.is_trading_day else "最近值得关注的新进入 AI 主线公司"
    return f"""# AI Theme Intelligence System - {today.isoformat()}

## 0. 报告模式
{fallback_market_mode_section(market_mode)}

## 1. 今日市场主线
{fallback_main_line(primary_narrative, market_mode)}

## 2. Narrative Shift（叙事迁移）
{format_narrative_shifts(narrative_shifts)}

## 3. AI Sector Heatmap（AI 板块热度图）
{fallback_heatmap_section(theme_signals)}

## 4. {dynamic_title}
{format_movers(movers)}

## 5. 深度公司研究
{fallback_company_research_v2(research_company, rerating_profile)}

## 6. AI Industry Chain Mapping（AI 产业链关系图）
{format_relationship_chain(relationship_chain)}

这条关系图的意义在于：AI 投资不能只看单家公司，而要看瓶颈从哪一层转移到哪一层。利润通常流向控制瓶颈、生态或客户预算入口的环节。

## 7. Thesis Tracking（长期 thesis 跟踪）
{format_thesis_table(theses)}

## 8. 精选新闻证据
{fallback_news_section(top_news, companies)}

## 9. Thinking Questions（思考问题）
- 当前 AI 主线里，什么还没有被 fully priced in？
- 产业链哪一层真正赚最多利润：芯片、网络、电力、散热、软件，还是平台入口？
- 这家公司是趋势受益者，还是价值捕获者？
- 谁控制 ecosystem，谁只是可替换供应商？
- 这个 narrative 是短期交易，还是长期产业迁移？

> 当前为 {mode_label}。如果是非交易日，本报告刻意降低“今日股价异动”权重，把重点放在产业结构、thesis tracking 和重估触发器上。
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
    market_mode = get_market_mode(today)
    news = fetch_market_news(companies)
    featured_news = select_top_news(news, companies, limit=1)
    if featured_news:
        enrich_article_text(featured_news[0])

    theme_signals = build_theme_heatmap(news, companies)
    narrative_shifts = detect_narrative_shifts(theme_signals)
    primary_narrative = infer_primary_narrative(theme_signals, market_mode)
    movers = scan_dynamic_movers(news, market_mode)
    relationship_chain = build_relationship_chain(theme_signals)
    rerating_profile = build_rerating_profile(research_company)
    theses = build_thesis_table(theme_signals)

    prompt = build_llm_prompt(
        today=today,
        companies=companies,
        news=news,
        featured_news=featured_news,
        research_company=research_company,
        market_mode=market_mode,
        primary_narrative=primary_narrative,
        theme_signals=theme_signals,
        narrative_shifts=narrative_shifts,
        movers=movers,
        rerating_profile=rerating_profile,
        relationship_chain=relationship_chain,
        theses=theses,
    )
    llm_report = summarize_with_openai(prompt)
    content = llm_report or build_fallback_report(
        today=today,
        companies=companies,
        news=news,
        featured_news=featured_news,
        research_company=research_company,
        market_mode=market_mode,
        primary_narrative=primary_narrative,
        theme_signals=theme_signals,
        narrative_shifts=narrative_shifts,
        movers=movers,
        rerating_profile=rerating_profile,
        relationship_chain=relationship_chain,
        theses=theses,
    )

    report_path = write_report(content, today)
    print(f"[OK] 已生成报告: {report_path}")
    if not llm_report:
        print("[INFO] 未使用 OpenAI，总结为基础模板。配置 OPENAI_API_KEY 后可生成更完整中文分析。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

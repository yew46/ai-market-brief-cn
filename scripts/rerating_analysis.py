"""公司重估与护城河分析。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EARLY_NARRATIVE = {"AMBA", "QCOM", "GEV", "VST", "CEG", "TSLA"}
FULLY_PRICED = {"NVDA", "AVGO"}
PARTIALLY_PRICED = {"AMD", "TSM", "ANET", "VRT", "MSFT", "AAPL"}


@dataclass
class ReratingProfile:
    """公司研究框架。"""

    ticker: str
    market_perception: str
    bull_case: str
    bear_case: str
    rerating_trigger: str
    moat_analysis: dict[str, str]
    price_in_status: str
    key_metrics: list[str]


def infer_price_in_status(ticker: str) -> str:
    """粗略判断市场是否已经定价。"""

    if ticker in FULLY_PRICED:
        return "fully priced in"
    if ticker in PARTIALLY_PRICED:
        return "partially priced in"
    if ticker in EARLY_NARRATIVE:
        return "early narrative"
    return "underfollowed"


def build_rerating_profile(company: dict[str, Any]) -> ReratingProfile:
    """基于 watchlist 信息构建重估分析模板。"""

    ticker = company["ticker"]
    theme = company.get("所属主题", "")
    logic = company.get("核心观察逻辑", "")
    status = infer_price_in_status(ticker)

    return ReratingProfile(
        ticker=ticker,
        market_perception=f"市场通常把 {ticker} 放在 `{theme}` 框架下定价，核心分歧是这条主线能否转化成持续收入和利润。",
        bull_case=f"多头在赌：{logic} 如果连续几个季度被财报验证，公司估值框架会从周期股/硬件股向 AI 结构性成长资产迁移。",
        bear_case="空头担忧：需求被提前透支、竞争压缩利润率、客户集中度过高，或者市场已经把未来多年增长提前计入估值。",
        rerating_trigger="真正的重估触发器通常不是一条新闻，而是收入增速、利润率、订单/设计导入、客户扩张和管理层指引同时改善。",
        moat_analysis={
            "ecosystem": "是否处在客户、开发者、供应链或平台生态的关键节点。",
            "switching cost": "客户替换供应商是否会带来工程、认证、软件迁移或产能风险。",
            "software stack": "是否有软件、工具链、API 或系统方案提升粘性。",
            "developer adoption": "开发者、OEM、云厂商或系统集成商是否愿意围绕它构建方案。",
            "scale advantage": "规模是否带来成本、供给、研发或客户覆盖优势。",
            "pricing power": "在供需紧张或性能领先时，是否能维持价格和毛利率。",
        },
        price_in_status=status,
        key_metrics=key_metrics_for_company(ticker),
    )


def key_metrics_for_company(ticker: str) -> list[str]:
    """每家公司需要跟踪的关键指标。"""

    mapping = {
        "NVDA": ["datacenter revenue growth", "networking revenue", "gross margin", "Blackwell supply", "inference mix"],
        "QCOM": ["handset revenue", "AI PC design wins", "automotive backlog", "NPU adoption", "margin trend"],
        "AMBA": ["CV revenue growth", "design wins", "automotive pipeline", "robotics / vision AI customers", "gross margin"],
        "AMD": ["MI accelerator revenue", "EPYC share", "datacenter margin", "customer concentration", "guidance"],
        "AVGO": ["AI ASIC revenue", "networking revenue", "VMware cash flow", "gross margin", "custom silicon customers"],
        "TSM": ["HPC revenue growth", "CoWoS capacity", "advanced node utilization", "capex", "gross margin"],
        "ANET": ["cloud titan revenue", "AI ethernet adoption", "backlog", "gross margin", "customer concentration"],
        "VRT": ["order growth", "backlog", "liquid cooling demand", "margin", "datacenter exposure"],
        "GEV": ["grid orders", "gas power backlog", "free cash flow", "margin improvement", "datacenter power demand"],
        "VST": ["power prices", "nuclear output", "PPA contracts", "capacity payments", "free cash flow"],
    }
    return mapping.get(ticker, ["revenue growth", "guidance", "gross margin", "order growth", "customer adoption"])

"""AI 市场叙事迁移识别。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from theme_clustering import ThemeSignal


NARRATIVE_SHIFTS = [
    ("training -> inference", ["Inference"], "从训练算力扩张转向推理成本、延迟和部署效率。"),
    ("GPU -> networking", ["Networking"], "AI 集群瓶颈可能从单卡算力转向互联、交换机和光模块。"),
    ("cloud AI -> edge AI", ["Edge AI", "AI PC"], "AI 从云端应用扩散到手机、PC、汽车和本地设备。"),
    ("chatbot -> physical AI", ["Robotics", "Physical AI"], "市场开始关注 AI 与现实世界执行系统的结合。"),
    ("AI model -> AI infrastructure", ["Datacenter", "Power", "Cooling"], "价值链从模型应用扩展到底层电力、散热和数据中心约束。"),
    ("datacenter -> power / cooling bottleneck", ["Power", "Cooling"], "数据中心扩张的边际瓶颈可能变成电力接入和散热能力。"),
]


@dataclass
class NarrativeShift:
    """叙事迁移判断。"""

    name: str
    importance: str
    beneficiaries: list[str]
    potential_losers: list[str]
    duration: str
    evidence: list[str]


def infer_primary_narrative(signals: list[ThemeSignal], market_mode: Any) -> str:
    """根据最热主题回答“市场真正交易的是什么”。"""

    hot = [signal for signal in signals if signal.score > 0]
    if not hot:
        return "目前新闻信号不足，核心主线需要继续从财报、会议和价格行为中验证。"

    top = hot[0]
    if market_mode.is_trading_day:
        return f"今天市场最可能在交易 `{top.theme}` 这条 AI 主线：价格和资金会围绕相关公司重新定价。"
    return f"最近最值得研究的 AI 主线是 `{top.theme}`：非交易日更适合检查它是否是长期产业迁移，而不是短期新闻。"


def detect_narrative_shifts(signals: list[ThemeSignal]) -> list[NarrativeShift]:
    """用主题热度推断可能的 narrative shift。"""

    score_by_theme = {signal.theme: signal.score for signal in signals}
    evidence_by_theme = {signal.theme: signal.evidence for signal in signals}
    shifts: list[NarrativeShift] = []

    for name, trigger_themes, importance in NARRATIVE_SHIFTS:
        score = sum(score_by_theme.get(theme, 0) for theme in trigger_themes)
        if score <= 0:
            continue

        evidence: list[str] = []
        for theme in trigger_themes:
            evidence.extend(evidence_by_theme.get(theme, []))

        shifts.append(
            NarrativeShift(
                name=name,
                importance=importance,
                beneficiaries=beneficiaries_for_shift(name),
                potential_losers=losers_for_shift(name),
                duration="偏长期产业趋势，但短期价格可能提前交易，需要用多个季度数据验证。",
                evidence=evidence[:3],
            )
        )

    return shifts[:4]


def beneficiaries_for_shift(name: str) -> list[str]:
    """给叙事迁移匹配潜在受益公司。"""

    mapping = {
        "training -> inference": ["NVDA", "AMD", "QCOM", "AAPL", "MSFT"],
        "GPU -> networking": ["NVDA", "ANET", "AVGO"],
        "cloud AI -> edge AI": ["QCOM", "AMBA", "AAPL", "TSLA"],
        "chatbot -> physical AI": ["NVDA", "TSLA", "AMBA"],
        "AI model -> AI infrastructure": ["NVDA", "ANET", "AVGO", "VRT", "GEV", "VST", "CEG"],
        "datacenter -> power / cooling bottleneck": ["VRT", "GEV", "VST", "CEG"],
    }
    return mapping.get(name, [])


def losers_for_shift(name: str) -> list[str]:
    """给叙事迁移匹配可能失去定价权的环节。"""

    mapping = {
        "training -> inference": ["只依赖训练周期的算力供应商", "缺少推理软件生态的芯片公司"],
        "GPU -> networking": ["单纯 GPU 叙事且缺少系统级方案的公司"],
        "cloud AI -> edge AI": ["只做云端推理、缺少端侧入口的应用公司"],
        "chatbot -> physical AI": ["缺少硬件、传感器或真实部署能力的纯 demo 公司"],
        "AI model -> AI infrastructure": ["模型同质化、缺少分发和成本优势的应用层公司"],
        "datacenter -> power / cooling bottleneck": ["无法获得电力接入或散热方案的数据中心项目"],
    }
    return mapping.get(name, [])

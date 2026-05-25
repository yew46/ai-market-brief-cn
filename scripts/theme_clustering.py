"""AI 主题热度分类。

用关键词把新闻和公司逻辑映射到 AI 产业主题，生成一个可解释的 heatmap。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


THEME_KEYWORDS: dict[str, list[str]] = {
    "GPU": ["gpu", "accelerator", "cuda", "h100", "h200", "blackwell", "mi300", "ai chip"],
    "Networking": ["networking", "ethernet", "infiniband", "switch", "optical", "interconnect", "backend"],
    "Edge AI": ["edge ai", "on-device", "端侧", "low power", "snapdragon", "vision ai"],
    "Robotics": ["robot", "robotics", "humanoid", "autonomous", "机器人"],
    "AI software": ["copilot", "agent", "ai software", "llm", "model", "enterprise ai"],
    "Power": ["power", "electricity", "grid", "nuclear", "ppa", "energy", "电力"],
    "Cooling": ["cooling", "liquid cooling", "thermal", "散热"],
    "Foundry": ["foundry", "tsmc", "advanced packaging", "cowos", "node", "wafer"],
    "AI PC": ["ai pc", "pc refresh", "npu", "windows ai"],
    "Datacenter": ["data center", "datacenter", "hyperscaler", "capex", "cloud"],
    "Inference": ["inference", "推理", "serving", "tokens", "latency"],
    "Physical AI": ["physical ai", "world model", "simulation", "digital twin"],
}


@dataclass
class ThemeSignal:
    """单个主题的热度信号。"""

    theme: str
    score: int
    evidence: list[str]


def text_for_item(item: Any) -> str:
    """把新闻对象压成可搜索文本。"""

    return f"{item.title} {item.summary} {getattr(item, 'article_text', '')} {item.query}".lower()


def build_theme_heatmap(news: list[Any], companies: list[dict[str, Any]]) -> list[ThemeSignal]:
    """根据新闻和 watchlist 生成主题热度。"""

    signals: list[ThemeSignal] = []
    for theme, keywords in THEME_KEYWORDS.items():
        score = 0
        evidence: list[str] = []

        for item in news:
            text = text_for_item(item)
            hits = [keyword for keyword in keywords if keyword in text]
            if hits:
                score += len(hits)
                if len(evidence) < 3:
                    evidence.append(item.title)

        signals.append(ThemeSignal(theme=theme, score=score, evidence=evidence))

    return sorted(signals, key=lambda signal: signal.score, reverse=True)


def theme_summary(signals: list[ThemeSignal]) -> dict[str, list[ThemeSignal]]:
    """把主题热度拆成最热、减弱、新出现、待验证。"""

    active = [signal for signal in signals if signal.score > 0]
    return {
        "hot": active[:3],
        "emerging": active[3:6],
        "weakening": [signal for signal in signals if signal.score == 0][:3],
        "needs_validation": active[:4],
    }

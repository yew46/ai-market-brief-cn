"""AI 产业链关系图生成。"""

from __future__ import annotations

from theme_clustering import ThemeSignal


RELATIONSHIP_MAPS = {
    "Datacenter": [
        "AI training / inference demand",
        "GPU and accelerator demand",
        "high-speed networking bottleneck",
        "power and cooling constraint",
        "datacenter infrastructure capex",
    ],
    "Edge AI": [
        "Edge AI adoption",
        "local inference demand",
        "low-power chip and NPU demand",
        "device ecosystem control",
        "QCOM / AMBA / AAPL type beneficiaries",
    ],
    "Robotics": [
        "Physical AI models",
        "vision and sensor stack",
        "edge inference hardware",
        "actuation and real-world deployment",
        "ROI validation through production use cases",
    ],
    "Power": [
        "AI datacenter expansion",
        "grid interconnection pressure",
        "PPA / nuclear / gas generation demand",
        "power equipment backlog",
        "utility and IPP rerating debate",
    ],
    "Networking": [
        "larger AI clusters",
        "east-west traffic growth",
        "ethernet / optical / switch demand",
        "cluster utilization improvement",
        "ANET / AVGO / NVDA networking exposure",
    ],
}


def build_relationship_chain(signals: list[ThemeSignal]) -> list[str]:
    """根据最热主题选择产业链关系图。"""

    for signal in signals:
        if signal.score > 0 and signal.theme in RELATIONSHIP_MAPS:
            return RELATIONSHIP_MAPS[signal.theme]
    return RELATIONSHIP_MAPS["Datacenter"]


def format_relationship_chain(chain: list[str]) -> str:
    """输出 Markdown 产业链关系。"""

    return "\n".join(f"{idx}. {node}" for idx, node in enumerate(chain, start=1))

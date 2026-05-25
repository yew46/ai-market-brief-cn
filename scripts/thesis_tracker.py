"""长期 AI thesis 跟踪。"""

from __future__ import annotations

from dataclasses import dataclass

from theme_clustering import ThemeSignal


@dataclass
class Thesis:
    """长期 thesis 状态。"""

    name: str
    status: str
    evidence: str
    needs_validation: str


BASE_THESES = [
    ("AI networking bottleneck", "NVDA / ANET / AVGO 网络收入和订单是否持续增长", "是否连续多个季度体现为收入和 backlog"),
    ("Edge AI adoption", "QCOM / AAPL / AMBA 新产品和 design wins", "用户是否真实使用端侧 AI，而不是只停留在发布会"),
    ("Robotics / Physical AI", "demo、融资、客户试点和视觉 AI 需求增加", "真实部署、ROI 和规模化订单"),
    ("AI power shortage", "数据中心扩张、电网排队、PPA 和核电叙事升温", "电力项目落地速度和长期合同质量"),
    ("Inference acceleration", "推理成本、延迟、tokens 服务需求成为管理层重点", "推理收入是否成为可披露增长项"),
]


def build_thesis_table(signals: list[ThemeSignal]) -> list[Thesis]:
    """根据主题热度更新 thesis 状态。"""

    score_by_theme = {signal.theme: signal.score for signal in signals}
    thesis_theme_map = {
        "AI networking bottleneck": "Networking",
        "Edge AI adoption": "Edge AI",
        "Robotics / Physical AI": "Robotics",
        "AI power shortage": "Power",
        "Inference acceleration": "Inference",
    }

    rows: list[Thesis] = []
    for name, evidence, validation in BASE_THESES:
        theme = thesis_theme_map.get(name, "")
        score = score_by_theme.get(theme, 0)
        if score >= 3:
            status = "accelerating"
        elif score > 0:
            status = "early / needs confirmation"
        else:
            status = "watching"
        rows.append(Thesis(name=name, status=status, evidence=evidence, needs_validation=validation))
    return rows

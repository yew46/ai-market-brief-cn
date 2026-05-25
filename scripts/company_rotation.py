"""公司轮换逻辑。

这个文件负责从 watchlist 中按日期选择当天要研究的公司。
设计目标是简单、可预测：同一天重复运行会选中同一家公司。
"""

from __future__ import annotations

from datetime import date
from typing import Any


def pick_company_for_date(companies: list[dict[str, Any]], target_date: date) -> dict[str, Any]:
    """按日期轮换选择一家公司。

    使用 2024-01-01 作为固定起点，避免依赖本地状态文件。
    """

    if not companies:
        raise ValueError("company_watchlist.json 不能为空")

    start = date(2024, 1, 1)
    index = (target_date - start).days % len(companies)
    return companies[index]

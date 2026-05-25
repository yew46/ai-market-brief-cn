"""美股交易日识别。

这个模块不依赖付费市场日历 API。它用 weekday + 美国主要节假日规则
判断是否大概率为美股交易日，足够支撑日报模式切换。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class MarketMode:
    """报告模式信息。"""

    is_trading_day: bool
    mode_name: str
    reason: str


def observed_date(day: date) -> date:
    """把落在周末的固定节假日转换为常见观察日。"""

    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """返回某月第 n 个 weekday，Monday=0。"""

    current = date(year, month, 1)
    while current.weekday() != weekday:
        current += timedelta(days=1)
    return current + timedelta(days=7 * (n - 1))


def last_weekday(year: int, month: int, weekday: int) -> date:
    """返回某月最后一个 weekday，Monday=0。"""

    current = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return current


def easter_date(year: int) -> date:
    """计算西方复活节日期，用于 Good Friday。"""

    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def us_market_holidays(year: int) -> set[date]:
    """返回常见美股休市日。

    这里覆盖主要规则，不处理所有特殊休市和半日交易。
    """

    juneteenth = observed_date(date(year, 6, 19)) if year >= 2022 else None
    holidays = {
        observed_date(date(year, 1, 1)),
        nth_weekday(year, 1, 0, 3),
        nth_weekday(year, 2, 0, 3),
        easter_date(year) - timedelta(days=2),
        last_weekday(year, 5, 0),
        observed_date(date(year, 7, 4)),
        nth_weekday(year, 9, 0, 1),
        nth_weekday(year, 11, 3, 4),
        observed_date(date(year, 12, 25)),
    }
    if juneteenth:
        holidays.add(juneteenth)
    return holidays


def get_market_mode(target_date: date) -> MarketMode:
    """判断报告应该使用交易日模式还是非交易日研究模式。"""

    if target_date.weekday() >= 5:
        return MarketMode(
            is_trading_day=False,
            mode_name="Non-Trading Day / Weekend Research Mode（非交易日研究模式）",
            reason="今天是周末，美股不交易，报告应偏长期产业研究和 thesis tracking。",
        )

    if target_date in us_market_holidays(target_date.year):
        return MarketMode(
            is_trading_day=False,
            mode_name="Non-Trading Day / Weekend Research Mode（非交易日研究模式）",
            reason="今天匹配美国主要节假日休市列表，报告应避免强行写股价异动。",
        )

    return MarketMode(
        is_trading_day=True,
        mode_name="Trading Day Mode（交易日模式）",
        reason="今天是工作日且未匹配主要美股休市日，报告可关注股价、成交量和板块轮动。",
    )

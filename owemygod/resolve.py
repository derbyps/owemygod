"""Turn a date expression into a calendar date. Code counts; the model never does."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from .schema import WEEKDAYS, WhenExpr


def _clamped(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _add_month(d: date) -> tuple[int, int]:
    return (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)


def next_day_of_month(day: int, today: date) -> date:
    """The next date with this day of month, today included; clamps 31 to short months."""
    day = max(1, min(day, 31))
    this = _clamped(today.year, today.month, day)
    return this if this >= today else _clamped(*_add_month(today), day)


def resolve_when(when: WhenExpr, today: date, payday_day: int = 25) -> date:
    t = when.type
    if t == "relative_days":
        return today + timedelta(days=when.n)
    if t == "weekday":
        return today + timedelta(days=(WEEKDAYS.index(when.day) - today.weekday()) % 7)
    if t == "next_week":
        return today + timedelta(days=7 - today.weekday())
    if t == "day_of_month":
        return next_day_of_month(when.day, today)
    if t == "payday":
        return next_day_of_month(payday_day, today)
    if t == "month_start":
        return date(*_add_month(today), 1)
    if t == "month_end":
        return _clamped(today.year, today.month, 31)
    raise ValueError(t)

from datetime import date

from owemygod.resolve import resolve_when
from owemygod.schema import WhenExpr

T = date(2026, 10, 23)  # Friday


def test_relative_days(): assert resolve_when(WhenExpr(type="relative_days", n=2), T) == date(2026, 10, 25)
def test_weekday_today_counts(): assert resolve_when(WhenExpr(type="weekday", day="fri"), T) == T
def test_weekday_next(): assert resolve_when(WhenExpr(type="weekday", day="mon"), T) == date(2026, 10, 26)
def test_next_week_is_monday(): assert resolve_when(WhenExpr(type="next_week"), T) == date(2026, 10, 26)
def test_day_of_month_rolls(): assert resolve_when(WhenExpr(type="day_of_month", day=20), T) == date(2026, 11, 20)
def test_day_of_month_this_month(): assert resolve_when(WhenExpr(type="day_of_month", day=28), T) == date(2026, 10, 28)
def test_day_31_clamps(): assert resolve_when(WhenExpr(type="day_of_month", day=31), date(2026, 11, 2)) == date(2026, 11, 30)
def test_payday_uses_setting(): assert resolve_when(WhenExpr(type="payday"), T, payday_day=25) == date(2026, 10, 25)
def test_payday_passed(): assert resolve_when(WhenExpr(type="payday"), date(2026, 10, 26)) == date(2026, 11, 25)
def test_month_start(): assert resolve_when(WhenExpr(type="month_start"), T) == date(2026, 11, 1)
def test_month_end(): assert resolve_when(WhenExpr(type="month_end"), T) == date(2026, 10, 31)
def test_month_end_december(): assert resolve_when(WhenExpr(type="month_start"), date(2026, 12, 5)) == date(2027, 1, 1)

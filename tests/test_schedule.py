from dataclasses import replace
from datetime import date, timedelta

from owemygod.schedule import (initial_state, mark_paid, next_rhythm_day, on_reminder_sent, on_reply, resume,
                               roll_day, todays_action)
from owemygod.schema import ReplyRead, WhenExpr

MON = date(2026, 10, 19)
WED = date(2026, 10, 21)
SUN = date(2026, 10, 18)
BASE = initial_state(None, "weekly", 0, SUN)  # next reminder Mon Oct 19, level 1


def test_next_rhythm_day_strictly_after(): assert next_rhythm_day("weekly", 0, MON) == date(2026, 10, 26)
def test_biweekly(): assert next_rhythm_day("biweekly", 0, MON) == date(2026, 11, 2)
def test_monthly(): assert next_rhythm_day("monthly", 25, MON) == date(2026, 10, 25)
def test_monthly_31_clamps(): assert next_rhythm_day("monthly", 31, date(2026, 11, 1)) == date(2026, 11, 30)
def test_monthly_after_day(): assert next_rhythm_day("monthly", 25, date(2026, 10, 25)) == date(2026, 11, 25)


def test_first_reminder_on_due_date():
    assert initial_state(WED, "weekly", 0, MON).next_nudge_on == WED


def test_first_reminder_next_rhythm_day():
    assert initial_state(None, "weekly", 0, WED).next_nudge_on == date(2026, 10, 26)


def test_due_date_in_past_means_today():
    assert initial_state(date(2026, 10, 1), "weekly", 0, MON).next_nudge_on == MON


def test_sent_raises_level_and_moves_on():
    s = on_reminder_sent(BASE, MON)
    assert (s.level, s.next_nudge_on) == (2, date(2026, 10, 26))


def test_level_caps_at_3():
    s = BASE
    for d in (MON, MON + timedelta(7), MON + timedelta(14), MON + timedelta(21)):
        s = on_reminder_sent(s, d)
    assert s.level == 3 and s.firm_count == 2


def test_remind_now_skips_rhythm_day_within_3_days():  # weekly Sunday, remind on Friday
    s = on_reminder_sent(initial_state(None, "weekly", 6, date(2026, 10, 20)), date(2026, 10, 23))
    assert s.next_nudge_on == date(2026, 11, 1)


def test_remind_now_keeps_rhythm_day_4_days_away():  # weekly Sunday, remind on Wednesday
    s = on_reminder_sent(initial_state(None, "weekly", 6, date(2026, 10, 19)), WED)
    assert s.next_nudge_on == date(2026, 10, 25)


def test_promise_pauses_and_flags_day():
    read = ReplyRead(kind="promise", when=WhenExpr(type="weekday", day="fri"))
    s = on_reply(BASE, read, date(2026, 10, 23), WED)
    assert s.promise_on == date(2026, 10, 23)
    assert todays_action(s, date(2026, 10, 23)) == "promised"
    assert todays_action(s, date(2026, 10, 22)) == "none"


def test_missed_promise_is_due_next_day_one_level_up():
    s = on_reply(BASE, ReplyRead(kind="promise", when=WhenExpr(type="weekday", day="fri")), date(2026, 10, 23), WED)
    s = roll_day(s, date(2026, 10, 24))
    assert todays_action(s, date(2026, 10, 24)) == "remind" and s.level == 2 and s.promise_on is None


def test_vague_keeps_rhythm():
    assert on_reply(BASE, ReplyRead(kind="vague"), None, WED).next_nudge_on == BASE.next_nudge_on


def test_reply_resets_firm_count():
    firm = replace(BASE, level=3, firm_count=2)
    assert on_reply(firm, ReplyRead(kind="vague"), None, WED).firm_count == 0


def test_talk_after_three_firm_ignored():
    s = replace(BASE, level=3, firm_count=3, next_nudge_on=MON)
    rolled = roll_day(s, MON)
    assert rolled.status == "talk" and todays_action(rolled, MON) == "none"


def test_resume():
    talk = replace(BASE, level=3, firm_count=3, status="talk")
    r = resume(talk, MON)
    assert (r.status, r.firm_count, r.next_nudge_on) == ("open", 0, MON)


def test_paid_has_no_action():
    assert todays_action(mark_paid(BASE), MON) == "none"


def test_overdue_stays_due():
    assert todays_action(BASE, WED) == "remind"

"""When to remind, and how firmly. Plain code; the model only reads replies and writes words.

Slow and steady: reminders follow the friend's rhythm, pause for promises, never come twice
within 3 days, and stop after three firm ones go unanswered.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Literal

from .resolve import next_day_of_month
from .schema import ReplyRead

Rhythm = Literal["weekly", "biweekly", "monthly"]
MIN_GAP_DAYS = 3
FIRM_LIMIT = 3


@dataclass(frozen=True)
class DebtState:
    rhythm: Rhythm
    rhythm_day: int  # weekday 0=Mon..6=Sun, or day of month 1..31
    level: int  # 1 gentle, 2 playful, 3 firm: the level of the next reminder
    firm_count: int  # firm reminders sent since the last reply
    next_nudge_on: date
    promise_on: date | None
    status: Literal["open", "talk", "paid"]


def next_rhythm_day(rhythm: Rhythm, rhythm_day: int, after: date) -> date:
    """The first rhythm day strictly after `after`."""
    if rhythm == "monthly":
        return next_day_of_month(rhythm_day, after + timedelta(days=1))
    d = after + timedelta(days=(rhythm_day - after.weekday() - 1) % 7 + 1)
    return d + timedelta(days=7) if rhythm == "biweekly" else d


def initial_state(due_on: date | None, rhythm: Rhythm, rhythm_day: int, today: date) -> DebtState:
    first = max(due_on, today) if due_on else next_rhythm_day(rhythm, rhythm_day, today)
    return DebtState(rhythm, rhythm_day, 1, 0, first, None, "open")


def on_reminder_sent(s: DebtState, today: date) -> DebtState:
    nxt = next_rhythm_day(s.rhythm, s.rhythm_day, today)
    if nxt <= today + timedelta(days=MIN_GAP_DAYS):
        nxt = next_rhythm_day(s.rhythm, s.rhythm_day, nxt)
    return replace(s, level=min(s.level + 1, 3), firm_count=s.firm_count + (s.level == 3),
                   next_nudge_on=nxt, promise_on=None)


def on_reply(s: DebtState, read: ReplyRead, resolved: date | None, today: date) -> DebtState:
    s = replace(s, firm_count=0, status="open" if s.status == "talk" else s.status)
    if read.kind == "promise" and resolved is not None:
        return replace(s, promise_on=resolved, next_nudge_on=resolved + timedelta(days=1))
    return s  # vague keeps the rhythm; claims_paid waits for the user to confirm


def roll_day(s: DebtState, today: date) -> DebtState:
    """Bring a state up to date at the start of a day."""
    if s.status != "open":
        return s
    if s.promise_on and s.promise_on < today:
        s = replace(s, promise_on=None, level=min(s.level + 1, 3), next_nudge_on=today)
    if s.firm_count >= FIRM_LIMIT and s.next_nudge_on <= today:
        s = replace(s, status="talk")
    return s


def todays_action(s: DebtState, today: date) -> Literal["remind", "promised", "none"]:
    if s.status != "open":
        return "none"
    if s.promise_on == today:
        return "promised"
    if s.promise_on is None and s.next_nudge_on <= today:
        return "remind"
    return "none"


def resume(s: DebtState, today: date) -> DebtState:
    return replace(s, status="open", firm_count=0, next_nudge_on=today, promise_on=None)


def mark_paid(s: DebtState) -> DebtState:
    return replace(s, status="paid", promise_on=None)

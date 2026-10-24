"""Scoring for evaluation and the RL reward.

Nudging before the promised date is rude and costs a friendship, so it is punished five times
harder than nudging late, which only costs a few days.
"""
from __future__ import annotations

from datetime import date

from .resolve import resolve_when
from .schema import ParseError, ReplyRead, parse_reply

R_EXACT, R_LATE, R_EARLY, R_WRONG_KIND, R_INVALID = 1.0, -1.0, -5.0, -2.0, -5.0


def score(pred: ReplyRead | None, gold: ReplyRead, today: date, payday_day: int = 25) -> dict:
    out = {"valid": pred is not None, "kind_ok": False, "exact": False, "early": False, "late": False}
    if pred is None or pred.kind != gold.kind:
        return out
    out["kind_ok"] = True
    if gold.kind != "promise":
        out["exact"] = True
        return out
    p, g = resolve_when(pred.when, today, payday_day), resolve_when(gold.when, today, payday_day)
    out["exact"], out["early"], out["late"] = p == g, p < g, p > g
    return out


def reward(text: str, gold: ReplyRead, today: date, payday_day: int = 25) -> float:
    try:
        pred = parse_reply(text)
    except ParseError:
        return R_INVALID
    s = score(pred, gold, today, payday_day)
    if not s["kind_ok"]:
        return R_WRONG_KIND
    if s["early"]:
        return R_EARLY
    if s["late"]:
        return R_LATE
    return R_EXACT

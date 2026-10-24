"""Keyword rules: the baseline the model must beat, and the fallback when the model is down."""
from __future__ import annotations

import re

from .schema import ReplyRead, WhenExpr

_DAYS = {"senin": "mon", "monday": "mon", "selasa": "tue", "tuesday": "tue", "rabu": "wed", "wednesday": "wed",
         "kamis": "thu", "thursday": "thu", "jumat": "fri", "jum'at": "fri", "friday": "fri", "sabtu": "sat",
         "saturday": "sat", "minggu": "sun", "sunday": "sun"}
_PAID = re.compile(r"\b(udah|sudah|already|barusan)\b.*\b(transfer|tf|kirim|send|sent|paid|bayar|lunas)\b"
                   r"|\b(paid you|sent it|udah masuk|cek mutasi)\b")
_PAYDAY = re.compile(r"\bgaji(an)?\b|\bpayday\b|\bget paid\b")
_START = re.compile(r"\bawal bulan\b|\b(early|start of|beginning of) next month\b|\bganti bulan\b")
_END = re.compile(r"\b(akhir|ujung) bulan\b|\bend of (the )?month\b|\bmonth ends\b")
_NEXT_WEEK = re.compile(r"\b(minggu|pekan) (depan|dpn)\b|\bnext week\b")
_DOM = re.compile(r"\b(?:tanggal|tgl|tg)\s?(\d{1,2})\b|\bthe (\d{1,2})(?:st|nd|rd|th)\b")
_IN_DAYS = re.compile(r"\b(\d)\s?(?:hari|hr) (?:lagi|lg)\b|\bin (\d) days\b")


def _promise(when: WhenExpr) -> ReplyRead:
    return ReplyRead(kind="promise", when=when)


def read_by_rules(reply: str) -> ReplyRead:
    t = reply.lower()
    if _PAID.search(t):
        return ReplyRead(kind="claims_paid")
    if _PAYDAY.search(t):
        return _promise(WhenExpr(type="payday"))
    if _START.search(t):
        return _promise(WhenExpr(type="month_start"))
    if _END.search(t):
        return _promise(WhenExpr(type="month_end"))
    if _NEXT_WEEK.search(t):
        return _promise(WhenExpr(type="next_week"))
    if m := _DOM.search(t):
        day = int(m.group(1) or m.group(2))
        if 1 <= day <= 31:
            return _promise(WhenExpr(type="day_of_month", day=day))
    if m := _IN_DAYS.search(t):
        return _promise(WhenExpr(type="relative_days", n=int(m.group(1) or m.group(2))))
    if re.search(r"\blusa\b|day after tomorrow", t):
        return _promise(WhenExpr(type="relative_days", n=2))
    if re.search(r"\b(besok|bsk|tomorrow|tmrw)\b", t):
        return _promise(WhenExpr(type="relative_days", n=1))
    if re.search(r"\b(hari ini|today|tonight|ntar sore|malem ini)\b", t):
        return _promise(WhenExpr(type="relative_days", n=0))
    for word, code in _DAYS.items():
        if re.search(rf"\b{re.escape(word)}\b", t):
            return _promise(WhenExpr(type="weekday", day=code))
    return ReplyRead(kind="vague")

"""The 09:00 morning nudge: at most one push per user per local day, none when nothing is due."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import db
from .schedule import roll_day, todays_action

PUSH_HOUR = 9


def summary(conn, user_id: int, today: date) -> str | None:
    remind, promised = [], []
    for d in db.list_debts(conn, user_id):
        s = roll_day(db.load_state(d), today)
        action = todays_action(s, today)
        if action == "remind":
            remind.append(d["friend_name"])
        elif action == "promised":
            promised.append(d["friend_name"])
    parts = []
    if remind:
        parts.append("Remind today: " + ", ".join(remind) + ".")
    if promised:
        names = promised[0] if len(promised) == 1 else ", ".join(promised[:-1]) + " and " + promised[-1]
        parts.append(f"{names} promised to pay today.")
    return " ".join(parts) or None


def due_users(conn, now_utc: datetime) -> list[tuple[int, date]]:
    out = []
    for u in db.list_users(conn):
        local = now_utc.astimezone(ZoneInfo(u["timezone"]))
        if local.hour >= PUSH_HOUR and not db.push_logged(conn, u["id"], local.date()):
            out.append((u["id"], local.date()))
    return out


def run_once(conn, now_utc: datetime, sender) -> int:
    """sender(sub, payload) -> bool (False = subscription gone). Returns pushes sent."""
    sent = 0
    for uid, today in due_users(conn, now_utc):
        db.log_push(conn, uid, today)
        text = summary(conn, uid, today)
        if not text:
            continue
        for sub in db.list_push_subscriptions(conn, uid):
            try:
                ok = sender(sub, {"title": "OweMyGod", "body": text, "url": "/"})
            except Exception:  # noqa: BLE001  one bad endpoint must not stop the others
                continue
            if ok:
                sent += 1
            else:
                db.delete_push_subscription(conn, sub["id"])
    return sent

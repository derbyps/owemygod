"""Turn database rows into what the screens show."""
from __future__ import annotations

from datetime import date

from owemygod.db import load_state
from owemygod.money import format_amount
from owemygod.schedule import todays_action

ORDER = {"remind": 0, "promised": 1, "waiting": 2, "next": 2, "talk": 3, "paid": 4}
LEVEL_NAMES = {1: "gentle", 2: "playful", 3: "firm"}


def _fmt_day(d: date, today: date) -> str:
    return f"{d:%a}" if 0 < (d - today).days <= 6 else f"{d:%b} {d.day}"


def preview(event: dict | None, currency: str) -> str:
    if not event:
        return ""
    kind, text, parsed = event["kind"], event.get("text"), event.get("parsed") or {}
    if kind == "excuse":
        return f'💬 "{text}"'
    if kind == "nudge":
        return f"📤 Reminder sent ({LEVEL_NAMES.get(parsed.get('level'), 'sent')})"
    if kind == "partial":
        return f"💵 Paid {format_amount(parsed.get('amount', 0), currency)}"
    if kind == "paid":
        return "✅ Paid in full"
    return f"💸 Lent{' for ' + text if text else ''}"


def home_rows(debts: list[dict], today: date) -> list[dict]:
    rows = []
    for d in debts:
        s = load_state(d)
        if s.status == "paid":
            badge, when = "paid", date.max
        elif s.status == "talk":
            badge, when = "talk", date.max
        else:
            action = todays_action(s, today)
            if action != "none":
                badge, when = action, today
            elif s.promise_on:
                badge, when = "waiting", s.promise_on
            else:
                badge, when = "next", s.next_nudge_on
        rows.append({"id": d["id"], "name": d["friend_name"], "initial": d["friend_name"][:1].upper(),
                     "amount_text": format_amount(d["remaining"], d["currency"]), "badge": badge, "when": when,
                     "today": today, "preview": preview(d.get("last_event"), d["currency"])})
    return sorted(rows, key=lambda r: (ORDER[r["badge"]], r["when"], r["name"].lower()))


def badge_text(row: dict) -> str:
    b = row["badge"]
    if b == "remind":
        return "Remind today"
    if b == "promised":
        return "Promised today"
    if b == "waiting":
        return f"Waiting until {row['when']:%b} {row['when'].day}"
    if b == "next":
        return f"Next: {_fmt_day(row['when'], row['today'])}"
    return "Talk in person" if b == "talk" else "Paid"

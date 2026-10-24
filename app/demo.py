"""Fictional friends for the judges' demo sandbox: one in every state the app can show."""
from __future__ import annotations

from datetime import date, timedelta

from owemygod import db
from owemygod.schedule import on_reminder_sent, on_reply, resume
from owemygod.schema import ReplyRead, WhenExpr


def seed_demo(conn, user_id: int, today: date) -> None:
    def debt(name, amount, item, lent_days_ago, currency="IDR"):
        did = db.create_debt(conn, user_id, friend_name=name, amount=amount, currency=currency, due_on=today,
                             item=item, rhythm="weekly", rhythm_day=today.weekday(),
                             today=today - timedelta(days=lent_days_ago))
        conn.execute("UPDATE debts SET lent_on = ? WHERE id = ?", ((today - timedelta(days=lent_days_ago)).isoformat(), did))
        return did, db.load_state(db.get_debt(conn, user_id, did))

    def nudge(did, s, on, text):
        db.add_event(conn, did, "nudge", text, {"level": s.level, "before": db.state_to_json(s)})
        return on_reminder_sent(s, on)

    def reply(did, s, text, read, resolved, on):
        db.add_event(conn, did, "excuse", text, {**read.model_dump(exclude_none=True),
                                                 "resolved": resolved.isoformat() if resolved else None,
                                                 "source": "model"})
        return on_reply(s, read, resolved, on)

    # 1. Sari: due today, first gentle reminder.
    did, s = debt("Sari", 200_000, "dinner at Senopati", 6)
    db.save_state(conn, did, s)

    # 2. Budi: said "jumat ya" last week; today is the promised day.
    did, s = debt("Budi", 150_000, "concert tickets", 12)
    s = nudge(did, s, today - timedelta(days=7), "Hey Budi! Gentle reminder ya soal yang Rp150k kemarin 🙏")
    s = reply(did, s, "sorry bgt lupa, nanti pas hari itu aku tf ya promise",
              ReplyRead(kind="promise", when=WhenExpr(type="relative_days", n=6)), today, today - timedelta(days=6))
    db.save_state(conn, did, s)

    # 3. Andi: "minggu depan ya", waiting.
    did, s = debt("Andi", 350_000, "kosan deposit", 9)
    s = nudge(did, s, today - timedelta(days=2), "Andi~ which is, the Rp350k masih nunggu kamu literally 😆")
    nxt = today + timedelta(days=7 - today.weekday())
    s = reply(did, s, "minggu depan ya bro, abis gajian literally langsung",
              ReplyRead(kind="promise", when=WhenExpr(type="next_week")), nxt, today - timedelta(days=1))
    db.save_state(conn, did, s)

    # 4. Rina: three firm reminders, no answer: talk in person.
    did, s = debt("Rina", 4000, "Bali villa share", 40, currency="USD")
    s = resume(s, today)
    for days_ago in (28, 21, 14, 7):
        s = nudge(did, s, today - timedelta(days=days_ago), "Hi Rina, I do need the $40 back. Can you tell me when? 🙏")
    db.save_state(conn, did, s.__class__(**{**s.__dict__, "status": "talk", "firm_count": 3}))

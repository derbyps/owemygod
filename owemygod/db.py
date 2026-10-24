"""SQLite storage. Every debt query is scoped by user id."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from datetime import date, datetime, timezone

from .schedule import DebtState, initial_state

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
  is_demo INTEGER NOT NULL DEFAULT 0, tone TEXT NOT NULL DEFAULT 'jaksel', payday_day INTEGER NOT NULL DEFAULT 25,
  timezone TEXT NOT NULL DEFAULT 'Asia/Jakarta', default_rhythm TEXT NOT NULL DEFAULT 'weekly',
  default_rhythm_day INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS debts (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  friend_name TEXT NOT NULL, phone TEXT, currency TEXT NOT NULL DEFAULT 'IDR', amount INTEGER NOT NULL,
  remaining INTEGER NOT NULL, item TEXT, lent_on TEXT NOT NULL, due_on TEXT,
  rhythm TEXT NOT NULL, rhythm_day INTEGER NOT NULL, level INTEGER NOT NULL, firm_count INTEGER NOT NULL,
  next_nudge_on TEXT NOT NULL, promise_on TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL,
  draft TEXT, draft_on TEXT, draft_source TEXT);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, debt_id INTEGER NOT NULL REFERENCES debts(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, text TEXT, parsed_json TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS push_subscriptions (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  endpoint TEXT UNIQUE NOT NULL, p256dh TEXT NOT NULL, auth TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS push_log (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, date TEXT NOT NULL,
  PRIMARY KEY (user_id, date));
CREATE TABLE IF NOT EXISTS model_calls (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, at TEXT NOT NULL);
"""
SETTINGS = ("tone", "payday_day", "timezone", "default_rhythm", "default_rhythm_day")


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def _hash(password: str, salt: bytes) -> str:
    return salt.hex() + ":" + hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def create_user(conn, username: str, password: str, *, is_demo: bool = False,
                timezone: str = "Asia/Jakarta") -> int:
    cur = conn.execute("INSERT INTO users (username, password_hash, is_demo, timezone, created_at) "
                       "VALUES (?, ?, ?, ?, ?)", (username, _hash(password, os.urandom(16)), int(is_demo),
                                                 timezone, _now()))
    return cur.lastrowid


def check_password(conn, username: str, password: str) -> int | None:
    row = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        return None
    salt_hex, _ = row["password_hash"].split(":")
    ok = hmac.compare_digest(row["password_hash"], _hash(password, bytes.fromhex(salt_hex)))
    return row["id"] if ok else None


def get_user(conn, user_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_name(conn, username: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def update_settings(conn, user_id: int, **fields) -> None:
    for k, v in fields.items():
        if k not in SETTINGS:
            raise ValueError(k)
        conn.execute(f"UPDATE users SET {k} = ? WHERE id = ?", (v, user_id))


def create_debt(conn, user_id: int, *, friend_name: str, amount: int, currency: str = "IDR",
                due_on: date | None, phone: str | None = None, item: str | None = None, rhythm: str,
                rhythm_day: int, today: date) -> int:
    s = initial_state(due_on, rhythm, rhythm_day, today)
    cur = conn.execute(
        "INSERT INTO debts (user_id, friend_name, phone, currency, amount, remaining, item, lent_on, due_on, rhythm, "
        "rhythm_day, level, firm_count, next_nudge_on, promise_on, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, friend_name, phone, currency, amount, amount, item, today.isoformat(),
         due_on.isoformat() if due_on else None, rhythm, rhythm_day, s.level, s.firm_count,
         s.next_nudge_on.isoformat(), None, s.status, _now()))
    add_event(conn, cur.lastrowid, "lent", item)
    return cur.lastrowid


def get_debt(conn, user_id: int, debt_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM debts WHERE id = ? AND user_id = ?", (debt_id, user_id)).fetchone()
    return dict(row) if row else None


def list_debts(conn, user_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM debts WHERE user_id = ? ORDER BY id", (user_id,))]


def load_state(row: dict) -> DebtState:
    return DebtState(row["rhythm"], row["rhythm_day"], row["level"], row["firm_count"],
                     date.fromisoformat(row["next_nudge_on"]),
                     date.fromisoformat(row["promise_on"]) if row["promise_on"] else None, row["status"])


def state_to_json(s: DebtState) -> dict:
    return {"rhythm": s.rhythm, "rhythm_day": s.rhythm_day, "level": s.level, "firm_count": s.firm_count,
            "next_nudge_on": s.next_nudge_on.isoformat(),
            "promise_on": s.promise_on.isoformat() if s.promise_on else None, "status": s.status}


def save_state(conn, debt_id: int, s: DebtState) -> None:
    j = state_to_json(s)
    conn.execute("UPDATE debts SET rhythm=?, rhythm_day=?, level=?, firm_count=?, next_nudge_on=?, promise_on=?, "
                 "status=? WHERE id=?", (*j.values(), debt_id))


def add_event(conn, debt_id: int, kind: str, text: str | None = None, parsed: dict | None = None,
              at: datetime | None = None) -> int:
    when = at.isoformat(timespec="seconds") if at else _now()
    cur = conn.execute("INSERT INTO events (debt_id, kind, text, parsed_json, created_at) VALUES (?, ?, ?, ?, ?)",
                       (debt_id, kind, text, json.dumps(parsed) if parsed is not None else None, when))
    return cur.lastrowid


def list_events(conn, debt_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM events WHERE debt_id = ? ORDER BY created_at DESC, id DESC", (debt_id,))
    return [{**dict(r), "parsed": json.loads(r["parsed_json"]) if r["parsed_json"] else None} for r in rows]


def get_event(conn, user_id: int, event_id: int) -> dict | None:
    row = conn.execute("SELECT e.* FROM events e JOIN debts d ON d.id = e.debt_id WHERE e.id = ? AND d.user_id = ?",
                       (event_id, user_id)).fetchone()
    return {**dict(row), "parsed": json.loads(row["parsed_json"]) if row["parsed_json"] else None} if row else None


def delete_event(conn, user_id: int, event_id: int) -> None:
    conn.execute("DELETE FROM events WHERE id = ? AND debt_id IN (SELECT id FROM debts WHERE user_id = ?)",
                 (event_id, user_id))


def record_payment(conn, debt_id: int, amount: int) -> int:
    row = conn.execute("SELECT remaining FROM debts WHERE id = ?", (debt_id,)).fetchone()
    remaining = max(0, row["remaining"] - amount)
    conn.execute("UPDATE debts SET remaining = ?, status = CASE WHEN ? = 0 THEN 'paid' ELSE status END, "
                 "promise_on = CASE WHEN ? = 0 THEN NULL ELSE promise_on END WHERE id = ?",
                 (remaining, remaining, remaining, debt_id))
    return remaining


def delete_old_demo_users(conn, older_than: datetime) -> None:
    conn.execute("DELETE FROM users WHERE is_demo = 1 AND created_at < ?", (older_than.isoformat(),))


def save_draft(conn, debt_id: int, text: str | None, on: date | None, source: str | None = None) -> None:
    conn.execute("UPDATE debts SET draft = ?, draft_on = ?, draft_source = ? WHERE id = ?",
                 (text, on.isoformat() if on else None, source, debt_id))


def count_model_calls(conn, user_id: int | None, since: datetime) -> int:
    q, args = "SELECT COUNT(*) FROM model_calls WHERE at >= ?", [since.isoformat()]
    if user_id is not None:
        q, args = q + " AND user_id = ?", args + [user_id]
    return conn.execute(q, args).fetchone()[0]


def log_model_call(conn, user_id: int) -> None:
    conn.execute("INSERT INTO model_calls (user_id, at) VALUES (?, ?)", (user_id, _now()))


def add_push_subscription(conn, user_id: int, sub: dict) -> None:
    conn.execute("INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth) VALUES (?, ?, ?, ?) "
                 "ON CONFLICT(endpoint) DO UPDATE SET user_id = excluded.user_id, p256dh = excluded.p256dh, "
                 "auth = excluded.auth", (user_id, sub["endpoint"], sub["keys"]["p256dh"], sub["keys"]["auth"]))


def list_push_subscriptions(conn, user_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM push_subscriptions WHERE user_id = ?", (user_id,))
    return [{"id": r["id"], "endpoint": r["endpoint"], "keys": {"p256dh": r["p256dh"], "auth": r["auth"]}}
            for r in rows]


def delete_push_subscription(conn, sub_id: int) -> None:
    conn.execute("DELETE FROM push_subscriptions WHERE id = ?", (sub_id,))


def list_users(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM users")]


def push_logged(conn, user_id: int, day: date) -> bool:
    return conn.execute("SELECT 1 FROM push_log WHERE user_id = ? AND date = ?",
                        (user_id, day.isoformat())).fetchone() is not None


def log_push(conn, user_id: int, day: date) -> None:
    conn.execute("INSERT OR IGNORE INTO push_log (user_id, date) VALUES (?, ?)", (user_id, day.isoformat()))

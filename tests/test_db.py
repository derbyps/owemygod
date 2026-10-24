from datetime import date, datetime, timedelta

from owemygod import db
from owemygod.schedule import initial_state

MON = date(2026, 10, 19)


def _debt(conn, user, **kw):
    args = dict(friend_name="Budi", amount=150_000, due_on=None, rhythm="weekly", rhythm_day=0, today=MON)
    return db.create_debt(conn, user, **{**args, **kw})


def test_password(conn):
    uid = db.create_user(conn, "me", "s3cret")
    assert db.check_password(conn, "me", "s3cret") == uid
    assert db.check_password(conn, "me", "nope") is None
    assert db.check_password(conn, "ghost", "s3cret") is None


def test_debts_scoped_by_user(conn):
    a, b = db.create_user(conn, "a", "pw"), db.create_user(conn, "b", "pw")
    d = _debt(conn, a)
    assert db.get_debt(conn, a, d)["friend_name"] == "Budi"
    assert db.get_debt(conn, b, d) is None
    assert db.list_debts(conn, b) == []


def test_create_debt_sets_schedule_and_lent_event(conn):
    u = db.create_user(conn, "a", "pw")
    d = db.get_debt(conn, u, _debt(conn, u, currency="USD", amount=4000))
    assert d["currency"] == "USD" and d["remaining"] == 4000
    assert db.load_state(d) == initial_state(None, "weekly", 0, MON)
    assert [e["kind"] for e in db.list_events(conn, d["id"])] == ["lent"]


def test_state_roundtrip(conn):
    u = db.create_user(conn, "a", "pw")
    d = _debt(conn, u)
    s = initial_state(date(2026, 10, 21), "monthly", 25, MON)
    db.save_state(conn, d, s)
    assert db.load_state(db.get_debt(conn, u, d)) == s


def test_partial_payment(conn):
    u = db.create_user(conn, "a", "pw")
    d = _debt(conn, u)
    assert db.record_payment(conn, d, 50_000) == 100_000
    assert db.get_debt(conn, u, d)["status"] == "open"
    assert db.record_payment(conn, d, 100_000) == 0
    assert db.get_debt(conn, u, d)["status"] == "paid"


def test_events_newest_first_and_delete_scoped(conn):
    a, b = db.create_user(conn, "a", "pw"), db.create_user(conn, "b", "pw")
    d = _debt(conn, a)
    e = db.add_event(conn, d, "excuse", "abis gajian ya", {"kind": "vague"})
    assert db.list_events(conn, d)[0]["id"] == e
    assert db.list_events(conn, d)[0]["parsed"] == {"kind": "vague"}
    db.delete_event(conn, b, e)
    assert db.list_events(conn, d)[0]["id"] == e
    db.delete_event(conn, a, e)
    assert all(x["id"] != e for x in db.list_events(conn, d))


def test_delete_old_demo_users(conn):
    old = db.create_user(conn, "demo-old", "x", is_demo=True)
    conn.execute("UPDATE users SET created_at = ? WHERE id = ?", ("2026-01-01T00:00:00", old))
    keep = db.create_user(conn, "me", "x")
    _debt(conn, old)
    db.delete_old_demo_users(conn, datetime(2026, 10, 1))
    assert db.get_user(conn, old) is None and db.get_user(conn, keep) is not None


def test_settings(conn):
    u = db.create_user(conn, "a", "pw", timezone="Asia/Makassar")
    db.update_settings(conn, u, tone="english", payday_day=1)
    user = db.get_user(conn, u)
    assert (user["tone"], user["payday_day"], user["timezone"]) == ("english", 1, "Asia/Makassar")

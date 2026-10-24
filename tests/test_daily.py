from datetime import date, datetime, timezone

import pytest

from owemygod import daily, db
from owemygod.schedule import on_reply
from owemygod.schema import ReplyRead, WhenExpr

UTC = timezone.utc
T = date(2026, 10, 24)  # Saturday


class FakeSender:
    def __init__(self, ok=True):
        self.sent, self.ok = [], ok

    def __call__(self, sub, payload):
        self.sent.append((sub["endpoint"], payload))
        return self.ok


@pytest.fixture
def wita_user(conn):
    uid = db.create_user(conn, "me", "pw", timezone="Asia/Makassar")
    db.add_push_subscription(conn, uid, {"endpoint": "https://push/1", "keys": {"p256dh": "k", "auth": "a"}})
    return uid


def _due_today(conn, uid, name="Sari"):
    return db.create_debt(conn, uid, friend_name=name, amount=1000, due_on=T, rhythm="weekly", rhythm_day=0, today=T)


def test_wita_before_9_not_due(conn, wita_user):
    assert daily.due_users(conn, datetime(2026, 10, 24, 0, 59, tzinfo=UTC)) == []  # 08:59 WITA


def test_wita_after_9_due(conn, wita_user):
    assert daily.due_users(conn, datetime(2026, 10, 24, 1, 0, tzinfo=UTC)) == [(wita_user, T)]


def test_once_per_day(conn, wita_user):
    _due_today(conn, wita_user)
    now = datetime(2026, 10, 24, 2, 0, tzinfo=UTC)
    assert daily.run_once(conn, now, FakeSender()) == 1
    assert daily.run_once(conn, now, FakeSender()) == 0


def test_no_push_when_nothing_due(conn, wita_user):
    s = FakeSender()
    assert daily.run_once(conn, datetime(2026, 10, 24, 2, 0, tzinfo=UTC), s) == 0 and s.sent == []


def test_summary_text(conn, wita_user):
    _due_today(conn, wita_user, "Sari")
    budi = db.create_debt(conn, wita_user, friend_name="Budi", amount=1000, due_on=None, rhythm="weekly",
                          rhythm_day=0, today=date(2026, 10, 20))
    s = db.load_state(db.get_debt(conn, wita_user, budi))
    db.save_state(conn, budi, on_reply(s, ReplyRead(kind="promise", when=WhenExpr(type="relative_days", n=1)), T,
                                       date(2026, 10, 23)))
    assert daily.summary(conn, wita_user, T) == "Remind today: Sari. Budi promised to pay today."


def test_gone_subscription_deleted(conn, wita_user):
    _due_today(conn, wita_user)
    daily.run_once(conn, datetime(2026, 10, 24, 2, 0, tzinfo=UTC), FakeSender(ok=False))
    assert db.list_push_subscriptions(conn, wita_user) == []

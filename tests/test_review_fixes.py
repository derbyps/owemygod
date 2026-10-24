"""Regression tests for the final review findings."""
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from owemygod import db
from owemygod.reader import Reader
from owemygod.resolve import next_day_of_month
from owemygod.writer import Writer
from tests.fakes import FakeClient

NOW = datetime(2026, 10, 23, 3, 0, tzinfo=timezone.utc)


@pytest.fixture
def app(tmp_path):
    a = create_app(str(tmp_path / "a.db"), reader=Reader(FakeClient('{"kind":"vague"}')),
                   writer=Writer(FakeClient("Hey {name}, {amount} ya")), clock=lambda: NOW, secret="t")
    db.create_user(a.state.conn, "me", "pw")
    return a


@pytest.fixture
def auth(app):
    c = TestClient(app)
    c.post("/login", data={"username": "me", "password": "pw"})
    return c


def _form(**kw):
    return {"friend_name": "Budi", "amount": "150k", "currency": "IDR", **kw}


# 1. monthly rhythm
def test_next_day_of_month_zero_is_guarded():
    assert next_day_of_month(0, date(2026, 10, 23)) == date(2026, 11, 1)


def test_new_monthly_debt_uses_month_day(auth, app):
    r = auth.post("/debts/new", data=_form(rhythm="monthly", rhythm_weekday="0", rhythm_monthday="25"),
                  follow_redirects=False)
    assert r.status_code == 303
    d = db.list_debts(app.state.conn, 1)[0]
    assert (d["rhythm"], d["rhythm_day"], d["next_nudge_on"]) == ("monthly", 25, "2026-10-25")


def test_new_weekly_debt_uses_weekday(auth, app):
    auth.post("/debts/new", data=_form(rhythm="weekly", rhythm_weekday="4", rhythm_monthday="25"))
    assert db.list_debts(app.state.conn, 1)[0]["rhythm_day"] == 4


def test_monthly_bad_day_is_form_error(auth):
    assert auth.post("/debts/new", data=_form(rhythm="monthly", rhythm_monthday="0")).status_code == 400


def test_monthly_default_from_settings_does_not_crash(auth, app):
    db.update_settings(app.state.conn, 1, default_rhythm="monthly", default_rhythm_day=0)
    assert auth.post("/debts/new", data=_form(), follow_redirects=False).status_code == 303


# 2. ids are never reused, so an old cookie can't open a newer account
def test_user_ids_not_reused(app):
    conn = app.state.conn
    demo = db.create_user(conn, "demo-x", "pw", is_demo=True)
    conn.execute("UPDATE users SET created_at = '2000-01-01T00:00:00' WHERE id = ?", (demo,))
    db.delete_old_demo_users(conn, datetime(2026, 1, 1))
    assert db.create_user(conn, "later", "pw") != demo


def test_stale_session_is_logged_out(app):
    c = TestClient(app)
    c.post("/demo")
    conn = app.state.conn
    conn.execute("UPDATE users SET created_at = '2000-01-01T00:00:00' WHERE is_demo = 1")
    db.delete_old_demo_users(conn, datetime(2026, 1, 1))
    assert c.get("/settings", follow_redirects=False).status_code == 303


# 3. loose input → 400, not 500
@pytest.mark.parametrize("data", [_form(amount="99999999999999999999999"), _form(due_on="23/10/2026")])
def test_new_debt_bad_input_400(auth, data):
    assert auth.post("/debts/new", data=data).status_code == 400


def _debt(auth):
    return int(auth.post("/debts/new", data=_form(), follow_redirects=False).headers["location"].rsplit("/", 1)[1])


@pytest.mark.parametrize("extra", [{"read": "not json"}, {"read": '{"kind":"vague"}', "fixed_date": "tomorrow"}])
def test_reply_confirm_bad_input_400(auth, extra):
    d = _debt(auth)
    assert auth.post(f"/debts/{d}/reply/confirm", data={"text": "x", "source": "model", **extra}).status_code == 400


def test_fixed_date_in_past_rejected(auth):
    d = _debt(auth)
    r = auth.post(f"/debts/{d}/reply/confirm", data={"text": "x", "source": "model", "read": '{"kind":"vague"}',
                                                     "fixed_date": "2026-10-01"})
    assert r.status_code == 400


# 4. a failing push service doesn't 500 the test button
def test_push_test_survives_sender_error(app, auth):
    def boom(sub, payload):
        raise RuntimeError("push service down")
    app.state.push_sender = boom
    auth.post("/push/subscribe", json={"endpoint": "https://push/x", "keys": {"p256dh": "k", "auth": "a"}})
    r = auth.post("/push/test")
    assert r.status_code == 200 and r.json() == {"sent": 0, "failed": 1}


# 8. a partial payment counts as a response
def test_partial_payment_resets_firm_count(auth, app):
    d = _debt(auth)
    app.state.conn.execute("UPDATE debts SET level = 3, firm_count = 2 WHERE id = ?", (d,))
    auth.post(f"/debts/{d}/partial", data={"amount": "50k"})
    assert db.get_debt(app.state.conn, 1, d)["firm_count"] == 0


# 10. trying the demo on your own phone doesn't steal your morning pushes
def test_demo_subscription_does_not_take_owner_endpoint(app):
    conn = app.state.conn
    sub = {"endpoint": "https://push/phone", "keys": {"p256dh": "k", "auth": "a"}}
    db.add_push_subscription(conn, 1, sub)
    demo = db.create_user(conn, "demo-y", "pw", is_demo=True)
    db.add_push_subscription(conn, demo, sub)
    conn.execute("UPDATE users SET created_at = '2000-01-01T00:00:00' WHERE id = ?", (demo,))
    db.delete_old_demo_users(conn, datetime(2026, 1, 1))
    assert [s["endpoint"] for s in db.list_push_subscriptions(conn, 1)] == ["https://push/phone"]


# double tap on Remind now / Regenerate must not pay for two drafts
def test_double_tap_draft_calls_model_once(app, auth):
    fc = FakeClient("Hey {name}, {amount} ya")
    app.state.writer = Writer(fc)
    d = _debt(auth)
    auth.post(f"/debts/{d}/draft")
    auth.post(f"/debts/{d}/draft")
    assert fc.calls == 1


def test_loading_labels_on_model_buttons(auth):
    d = _debt(auth)
    page = auth.get(f"/debts/{d}").text
    assert 'data-loading="Writing…"' in page and 'data-loading="Reading…"' in page

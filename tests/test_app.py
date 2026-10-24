from datetime import datetime, timezone
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from owemygod import db
from owemygod.reader import Reader
from owemygod.writer import Writer
from tests.fakes import FakeClient

NOW = datetime(2026, 10, 23, 3, 0, tzinfo=timezone.utc)  # Friday 10:00 WIB


@pytest.fixture
def app(tmp_path):
    a = create_app(str(tmp_path / "app.db"), reader=Reader(FakeClient('{"kind":"promise","when":{"type":"payday"}}')),
                   writer=Writer(FakeClient("Hey {name}, {amount} ya 🙏")), clock=lambda: NOW, secret="test")
    db.create_user(a.state.conn, "me", "pw")
    return a


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth(client):
    client.post("/login", data={"username": "me", "password": "pw"})
    return client


def _new(auth, **kw):
    r = auth.post("/debts/new", data={"friend_name": "Budi", "amount": "150k", "currency": "IDR", **kw},
                  follow_redirects=False)
    assert r.status_code == 303
    return int(r.headers["location"].rsplit("/", 1)[1])


def test_requires_login(client): assert client.get("/", follow_redirects=False).status_code == 303
def test_bad_login(client): assert "Wrong" in client.post("/login", data={"username": "me", "password": "x"}).text
def test_healthz(client): assert client.get("/healthz").json() == {"ok": True, "reader": True, "writer": True}


def test_demo_has_four_rows(client):
    client.post("/demo")
    assert client.get("/").text.count('class="row') == 4


def test_new_debt_minimal(auth):
    _new(auth)
    assert "Budi" in auth.get("/").text and "Rp150k" in auth.get("/").text


def test_new_debt_usd(auth):
    _new(auth, friend_name="Sam", amount="40", currency="USD")
    assert "$40" in auth.get("/").text


def test_new_debt_bad_amount(auth):
    r = auth.post("/debts/new", data={"friend_name": "B", "amount": "abc", "currency": "IDR"})
    assert r.status_code == 400 and "Amount" in r.text


def test_due_today_shows_draft(auth):
    d = _new(auth, due_on="2026-10-23")
    page = auth.get(f"/debts/{d}").text
    assert "Hey Budi, Rp150k ya 🙏" in page and "Remind today" in auth.get("/").text


def test_reply_promise_flow(auth):
    d = _new(auth)
    preview = auth.post(f"/debts/{d}/reply", data={"text": "abis gajian ya"}).text
    assert "Promise" in preview and "Oct 25" in preview
    auth.post(f"/debts/{d}/reply/confirm", data={"text": "abis gajian ya", "read": '{"kind":"promise","when":{"type":"payday"}}', "source": "model"})
    assert "Waiting until Oct 25" in auth.get("/").text
    assert "abis gajian ya" in auth.get(f"/debts/{d}").text


def test_reply_fixed_date(auth):
    d = _new(auth)
    auth.post(f"/debts/{d}/reply/confirm", data={"text": "x", "read": '{"kind":"promise","when":{"type":"payday"}}',
                                                 "source": "model", "fixed_date": "2026-10-30"})
    assert "Waiting until Oct 30" in auth.get("/").text


def test_sent_redirects_to_whatsapp_and_undo_restores(auth, app):
    d = _new(auth, due_on="2026-10-23", phone="0812-3456-789")
    r = auth.post(f"/debts/{d}/sent", data={"text": "Hey Budi 🙏"}, follow_redirects=False)
    assert r.headers["location"].startswith("https://wa.me/628123456789?text=")
    row = db.get_debt(app.state.conn, 1, d)
    assert row["level"] == 2
    ev = db.list_events(app.state.conn, d)[0]
    auth.post(f"/events/{ev['id']}/undo")
    assert db.get_debt(app.state.conn, 1, d)["level"] == 1


def test_demo_send_link_has_no_number(client, app):
    client.post("/demo")
    did = [r for r in db.list_debts(app.state.conn, 2)][0]["id"]
    r = client.post(f"/debts/{did}/sent", data={"text": "hi"}, follow_redirects=False)
    assert unquote(r.headers["location"]).startswith("https://wa.me/?text=hi")


def test_cannot_see_others_debt(auth, app):
    other = db.create_user(app.state.conn, "x", "pw")
    from datetime import date
    d = db.create_debt(app.state.conn, other, friend_name="Z", amount=1000, due_on=None, rhythm="weekly",
                       rhythm_day=0, today=date(2026, 10, 23))
    assert auth.get(f"/debts/{d}").status_code == 404
    assert auth.post(f"/debts/{d}/paid").status_code == 404


def test_partial_then_paid(auth):
    d = _new(auth)
    auth.post(f"/debts/{d}/partial", data={"amount": "50k"})
    assert "Rp100k" in auth.get("/").text
    auth.post(f"/debts/{d}/paid")
    assert "Paid" in auth.get("/").text and "LUNAS" in auth.get(f"/debts/{d}").text


def test_claims_paid_asks_to_check(app, auth):
    app.state.reader = Reader(FakeClient('{"kind":"claims_paid"}'))
    d = _new(auth)
    assert "Check your bank" in auth.post(f"/debts/{d}/reply", data={"text": "udah aku tf"}).text


def test_settings_saved(auth, app):
    auth.post("/settings", data={"tone": "english", "payday_day": "1", "timezone": "Asia/Makassar",
                                 "default_rhythm": "weekly", "default_rhythm_day": "6"})
    u = db.get_user(app.state.conn, 1)
    assert (u["tone"], u["payday_day"], u["timezone"], u["default_rhythm_day"]) == ("english", 1, "Asia/Makassar", 6)


def test_vapid_key_route(app, client):
    app.state.vapid_public = "PUBKEY"
    assert client.get("/vapid-public-key").json() == {"key": "PUBKEY"}


def test_subscribe_and_test_push(app, auth):
    sent = []
    app.state.push_sender = lambda sub, payload: sent.append((sub["endpoint"], payload)) or True
    r = auth.post("/push/subscribe", json={"endpoint": "https://push/x", "keys": {"p256dh": "k", "auth": "a"}})
    assert r.status_code == 204
    assert auth.post("/push/test").json() == {"sent": 1}
    assert sent[0][0] == "https://push/x" and "OweMyGod" in sent[0][1]["title"]


def test_push_test_without_subscription(app, auth):
    app.state.push_sender = lambda sub, payload: True
    assert auth.post("/push/test").json() == {"sent": 0}


def test_service_worker_served_at_root(client):
    r = client.get("/sw.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"] and "showNotification" in r.text


def test_manifest_served(client):
    assert client.get("/static/manifest.webmanifest").json()["display"] == "standalone"

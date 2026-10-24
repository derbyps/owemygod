"""OweMyGod web app: a list of friends who owe you, gentle reminders, a log of their replies."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from owemygod import daily, db, push
from owemygod.model_client import from_env
from owemygod.money import CURRENCIES, format_amount, parse_amount, totals
from owemygod.phone import normalize, wa_link
from owemygod.reader import Reader
from owemygod.resolve import resolve_when
from owemygod.schedule import (DebtState, mark_paid, on_reminder_sent, on_reply, resume, roll_day,
                               todays_action)
from owemygod.schema import ReplyRead
from owemygod.writer import Writer

from . import views
from .demo import seed_demo

HERE = Path(__file__).resolve().parent
TIMEZONES = {"Asia/Jakarta": "WIB", "Asia/Makassar": "WITA", "Asia/Jayapura": "WIT"}
TONES = {"jaksel": "Jaksel mix", "english": "English", "bahasa": "Bahasa"}
RHYTHMS = {"weekly": "Every week", "biweekly": "Every 2 weeks", "monthly": "Every month"}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
KIND_TEXT = {"promise": "Promise", "vague": "No date yet", "claims_paid": "Says they've paid"}
WHEN_TEXT = {"relative_days": None, "weekday": None, "next_week": "next week", "day_of_month": None,
             "payday": "after payday", "month_start": "start of the month", "month_end": "end of the month"}


def _when_text(read: ReplyRead) -> str:
    w = read.when
    if w is None:
        return ""
    if w.type == "relative_days":
        return {0: "today", 1: "tomorrow", 2: "the day after tomorrow"}.get(w.n, f"in {w.n} days")
    if w.type == "weekday":
        return WEEKDAYS[["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(w.day)]
    if w.type == "day_of_month":
        return f"on the {w.day}th"
    return WHEN_TEXT[w.type]


def create_app(db_path: str, reader: Reader, writer: Writer, clock=lambda: datetime.now(timezone.utc),
               secret: str | None = None, demo_calls_per_hour: int = 20, calls_per_day: int = 500) -> FastAPI:
    app = FastAPI(title="OweMyGod", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=secret or secrets.token_hex(32), same_site="lax",
                       https_only=False, max_age=60 * 60 * 24 * 60)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    app.state.conn = db.connect(db_path)
    app.state.reader, app.state.writer, app.state.clock = reader, writer, clock
    app.state.vapid_public, app.state.push_sender = None, None
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["day"] = lambda iso: f"{datetime.fromisoformat(iso):%a, %b} {datetime.fromisoformat(iso).day}"
    templates.env.globals.update(badge_text=views.badge_text, fmt=format_amount, TONES=TONES, RHYTHMS=RHYTHMS,
                                 WEEKDAYS=WEEKDAYS, TIMEZONES=TIMEZONES, CURRENCIES=CURRENCIES,
                                 LEVEL_NAMES=views.LEVEL_NAMES)
    conn = app.state.conn

    # ---- helpers -------------------------------------------------------------------------------
    def user_or_redirect(request: Request) -> dict | None:
        uid = request.session.get("uid")
        return db.get_user(conn, uid) if uid else None

    def today_for(user: dict) -> date:
        return app.state.clock().astimezone(ZoneInfo(user["timezone"])).date()

    def page(request: Request, name: str, status: int = 200, **ctx) -> HTMLResponse:
        return templates.TemplateResponse(request, name, ctx, status_code=status)

    def owned_debt(user: dict, debt_id: int) -> dict:
        d = db.get_debt(conn, user["id"], debt_id)
        if not d:
            raise HTTPException(404)
        return d

    def fresh_state(d: dict, today: date):
        s = db.load_state(d)
        rolled = roll_day(s, today)
        if rolled != s:
            db.save_state(conn, d["id"], rolled)
        return rolled

    def model_allowed(user: dict) -> bool:
        now = app.state.clock().replace(tzinfo=None)
        if db.count_model_calls(conn, None, now - timedelta(days=1)) >= calls_per_day:
            return False
        if user["is_demo"] and db.count_model_calls(conn, user["id"], now - timedelta(hours=1)) >= demo_calls_per_hour:
            return False
        db.log_model_call(conn, user["id"])
        return True

    def reader_for(user: dict) -> Reader:
        return app.state.reader if model_allowed(user) else Reader(None)

    def writer_for(user: dict) -> Writer:
        return app.state.writer if model_allowed(user) else Writer(None)

    def make_draft(user: dict, d: dict, level: int, today: date) -> None:
        replies = [e["text"] for e in reversed(db.list_events(conn, d["id"])) if e["kind"] == "excuse"]
        days = (today - date.fromisoformat(d["lent_on"])).days
        text, source = writer_for(user).draft(level=level, tone=user["tone"], item=d["item"], days_since=days,
                                              replies=replies[-2:], name=d["friend_name"], amount=d["remaining"],
                                              currency=d["currency"])
        db.save_draft(conn, d["id"], text, today, source)

    def login_required(request: Request):
        user = user_or_redirect(request)
        if not user:
            raise HTTPException(303, headers={"Location": "/login"})
        return user

    @app.exception_handler(HTTPException)
    async def _http_exc(request: Request, exc: HTTPException):
        if exc.status_code == 303:
            return RedirectResponse(exc.headers["Location"], status_code=303)
        return HTMLResponse(f"<h1>{exc.status_code}</h1>", status_code=exc.status_code)

    # ---- auth & demo ---------------------------------------------------------------------------
    @app.get("/healthz")
    def healthz():
        return {"ok": True, "reader": app.state.reader.client is not None,
                "writer": app.state.writer.client is not None}

    @app.get("/login")
    def login_form(request: Request):
        return page(request, "login.html", error=None)

    @app.post("/login")
    def login(request: Request, username: str = Form(...), password: str = Form(...)):
        uid = db.check_password(conn, username.strip(), password)
        if not uid:
            return page(request, "login.html", 401, error="Wrong username or password.")
        request.session["uid"] = uid
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.post("/demo")
    def demo(request: Request):
        uid = db.create_user(conn, f"demo-{secrets.token_hex(6)}", secrets.token_hex(16), is_demo=True)
        user = db.get_user(conn, uid)
        seed_demo(conn, uid, today_for(user))
        request.session["uid"] = uid
        return RedirectResponse("/", status_code=303)

    # ---- home & debts --------------------------------------------------------------------------
    @app.get("/")
    def home(request: Request):
        user = login_required(request)
        today = today_for(user)
        debts = []
        for d in db.list_debts(conn, user["id"]):
            fresh_state(d, today)
            d = db.get_debt(conn, user["id"], d["id"])
            events = db.list_events(conn, d["id"])
            debts.append({**d, "last_event": events[0] if events else None})
        return page(request, "home.html", user=user, rows=views.home_rows(debts, today), total=totals(debts))

    @app.get("/debts/new")
    def new_form(request: Request):
        user = login_required(request)
        return page(request, "new.html", user=user, error=None, form={})

    @app.post("/debts/new")
    def new_debt(request: Request, friend_name: str = Form(...), amount: str = Form(...),
                 currency: str = Form("IDR"), due_on: str = Form(""), phone: str = Form(""), item: str = Form(""),
                 rhythm: str = Form(""), rhythm_day: str = Form("")):
        user = login_required(request)
        form = dict(friend_name=friend_name, amount=amount, currency=currency, due_on=due_on, phone=phone,
                    item=item, rhythm=rhythm, rhythm_day=rhythm_day)
        currency = currency if currency in CURRENCIES else "IDR"
        try:
            value = parse_amount(amount, currency)
        except ValueError:
            return page(request, "new.html", 400, user=user, form=form,
                        error="Amount: try 150k, 1.2jt or Rp 150.000 (or 40 / 12.50 for $).")
        name = friend_name.strip()[:40]
        if not name:
            return page(request, "new.html", 400, user=user, form=form, error="Name: who owes you?")
        rhythm = rhythm if rhythm in RHYTHMS else user["default_rhythm"]
        rday = int(rhythm_day) if rhythm_day.isdigit() else user["default_rhythm_day"]
        due = date.fromisoformat(due_on) if due_on else None
        did = db.create_debt(conn, user["id"], friend_name=name, amount=value, currency=currency, due_on=due,
                             phone=normalize(phone), item=item.strip()[:80] or None, rhythm=rhythm,
                             rhythm_day=rday, today=today_for(user))
        return RedirectResponse(f"/debts/{did}", status_code=303)

    @app.get("/debts/{debt_id}")
    def detail(request: Request, debt_id: int):
        user = login_required(request)
        today = today_for(user)
        d = owned_debt(user, debt_id)
        s = fresh_state(d, today)
        action = todays_action(s, today)
        d = db.get_debt(conn, user["id"], debt_id)
        if action == "remind" and d["draft_on"] != today.isoformat():
            make_draft(user, d, s.level, today)
            d = db.get_debt(conn, user["id"], debt_id)
        has_draft = d["draft"] and d["draft_on"] == today.isoformat() and s.status == "open"
        events = db.list_events(conn, debt_id)
        last_reply = next((e for e in events if e["kind"] == "excuse"), None)
        return page(request, "detail.html", user=user, d=d, s=s, action=action, events=events, today=today,
                    has_draft=has_draft, last_reply=last_reply, row=views.home_rows([{**d, "last_event": None}], today)[0])

    @app.post("/debts/{debt_id}/draft")
    def draft(request: Request, debt_id: int):
        user = login_required(request)
        today = today_for(user)
        d = owned_debt(user, debt_id)
        s = fresh_state(d, today)
        make_draft(user, d, s.level, today)
        return RedirectResponse(f"/debts/{debt_id}#reminder", status_code=303)

    @app.post("/debts/{debt_id}/sent")
    def sent(request: Request, debt_id: int, text: str = Form(...)):
        user = login_required(request)
        today = today_for(user)
        d = owned_debt(user, debt_id)
        s = fresh_state(d, today)
        db.add_event(conn, debt_id, "nudge", text, {"level": s.level, "before": db.state_to_json(s)})
        db.save_state(conn, debt_id, on_reminder_sent(s, today))
        db.save_draft(conn, debt_id, None, None)
        number = None if user["is_demo"] else d["phone"]
        return RedirectResponse(wa_link(number, text), status_code=303)

    @app.post("/events/{event_id}/undo")
    def undo(request: Request, event_id: int):
        user = login_required(request)
        e = db.get_event(conn, user["id"], event_id)
        if not e or e["kind"] != "nudge":
            raise HTTPException(404)
        b = e["parsed"]["before"]
        db.save_state(conn, e["debt_id"], DebtState(
            b["rhythm"], b["rhythm_day"], b["level"], b["firm_count"], date.fromisoformat(b["next_nudge_on"]),
            date.fromisoformat(b["promise_on"]) if b["promise_on"] else None, b["status"]))
        db.delete_event(conn, user["id"], event_id)
        return RedirectResponse(f"/debts/{e['debt_id']}", status_code=303)

    @app.post("/debts/{debt_id}/reply")
    def reply_preview(request: Request, debt_id: int, text: str = Form(...)):
        user = login_required(request)
        today = today_for(user)
        d = owned_debt(user, debt_id)
        text = text.strip()[:500]
        read, source = reader_for(user).read(text, today)
        resolved = resolve_when(read.when, today, user["payday_day"]) if read.when else None
        return page(request, "reply.html", user=user, d=d, text=text, read=read, source=source,
                    resolved=resolved, kind_text=KIND_TEXT[read.kind], when_text=_when_text(read),
                    read_json=read.model_dump_json(exclude_none=True), today=today)

    @app.post("/debts/{debt_id}/reply/confirm")
    def reply_confirm(request: Request, debt_id: int, text: str = Form(...), read: str = Form(...),
                      source: str = Form("rules"), fixed_date: str = Form("")):
        user = login_required(request)
        today = today_for(user)
        d = owned_debt(user, debt_id)
        r = ReplyRead.model_validate_json(read)
        if fixed_date:
            resolved = date.fromisoformat(fixed_date)
            if r.kind != "promise":
                r = ReplyRead(kind="promise", when={"type": "day_of_month", "day": resolved.day})
        else:
            resolved = resolve_when(r.when, today, user["payday_day"]) if r.when else None
        s = fresh_state(d, today)
        db.add_event(conn, debt_id, "excuse", text[:500], {**json.loads(r.model_dump_json(exclude_none=True)),
                                                          "resolved": resolved.isoformat() if resolved else None,
                                                          "source": source, "fixed": bool(fixed_date)})
        db.save_state(conn, debt_id, on_reply(s, r, resolved, today))
        db.save_draft(conn, debt_id, None, None)
        return RedirectResponse(f"/debts/{debt_id}", status_code=303)

    def _paid_state(user: dict, debt_id: int, today: date):
        d = db.get_debt(conn, user["id"], debt_id)
        db.save_state(conn, debt_id, mark_paid(fresh_state(d, today)))
        db.add_event(conn, debt_id, "paid")

    @app.post("/debts/{debt_id}/partial")
    def partial(request: Request, debt_id: int, amount: str = Form(...)):
        user = login_required(request)
        d = owned_debt(user, debt_id)
        try:
            value = parse_amount(amount, d["currency"])
        except ValueError:
            return RedirectResponse(f"/debts/{debt_id}?error=amount", status_code=303)
        value = min(value, d["remaining"])
        db.add_event(conn, debt_id, "partial", None, {"amount": value})
        if db.record_payment(conn, debt_id, value) == 0:
            _paid_state(user, debt_id, today_for(user))
        return RedirectResponse(f"/debts/{debt_id}", status_code=303)

    @app.post("/debts/{debt_id}/paid")
    def paid(request: Request, debt_id: int):
        user = login_required(request)
        d = owned_debt(user, debt_id)
        db.record_payment(conn, debt_id, d["remaining"])
        _paid_state(user, debt_id, today_for(user))
        return RedirectResponse(f"/debts/{debt_id}", status_code=303)

    @app.post("/debts/{debt_id}/resume")
    def resume_route(request: Request, debt_id: int):
        user = login_required(request)
        today = today_for(user)
        d = owned_debt(user, debt_id)
        db.save_state(conn, debt_id, resume(db.load_state(d), today))
        return RedirectResponse(f"/debts/{debt_id}", status_code=303)

    # ---- push ------------------------------------------------------------------------------------
    @app.get("/sw.js")
    def service_worker():
        return FileResponse(HERE / "static" / "sw.js", media_type="text/javascript",
                            headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})

    @app.get("/vapid-public-key")
    def vapid_key():
        return {"key": app.state.vapid_public}

    @app.post("/push/subscribe", status_code=204)
    async def subscribe(request: Request):
        user = login_required(request)
        sub = await request.json()
        if not str(sub.get("endpoint", "")).startswith("https://") or not sub.get("keys"):
            raise HTTPException(400)
        db.add_push_subscription(conn, user["id"], sub)

    @app.post("/push/test")
    def push_test(request: Request):
        user = login_required(request)
        sent = 0
        for sub in db.list_push_subscriptions(conn, user["id"]):
            ok = app.state.push_sender and app.state.push_sender(
                sub, {"title": "OweMyGod", "body": "Notifications work. See you at 09:00 when someone is due.",
                      "url": "/"})
            if ok:
                sent += 1
            elif ok is False:
                db.delete_push_subscription(conn, sub["id"])
        return {"sent": sent}

    # ---- settings ------------------------------------------------------------------------------
    @app.get("/settings")
    def settings_form(request: Request):
        user = login_required(request)
        return page(request, "settings.html", user=user, saved=False)

    @app.post("/settings")
    def settings(request: Request, tone: str = Form(...), payday_day: str = Form(...), timezone: str = Form(...),
                 default_rhythm: str = Form(...), default_rhythm_day: str = Form(...)):
        user = login_required(request)
        fields = {}
        if tone in TONES:
            fields["tone"] = tone
        if payday_day.isdigit() and 1 <= int(payday_day) <= 31:
            fields["payday_day"] = int(payday_day)
        if timezone in TIMEZONES:
            fields["timezone"] = timezone
        if default_rhythm in RHYTHMS:
            fields["default_rhythm"] = default_rhythm
        if default_rhythm_day.isdigit() and 0 <= int(default_rhythm_day) <= 31:
            fields["default_rhythm_day"] = int(default_rhythm_day)
        db.update_settings(conn, user["id"], **fields)
        return page(request, "settings.html", user=db.get_user(conn, user["id"]), saved=True)

    return app


def app_from_env() -> FastAPI:
    path = os.environ.get("OWEMYGOD_DB", "owemygod.db")
    app = create_app(path, Reader(from_env("OWEMYGOD_READER_PATH")), Writer(from_env("OWEMYGOD_WRITER_PATH")),
                     secret=os.environ.get("SECRET_KEY"),
                     demo_calls_per_hour=int(os.environ.get("OWEMYGOD_DEMO_MODEL_CALLS_PER_HOUR", "20")),
                     calls_per_day=int(os.environ.get("OWEMYGOD_MODEL_CALLS_PER_DAY", "500")))
    private, public = os.environ.get("VAPID_PRIVATE_KEY"), os.environ.get("VAPID_PUBLIC_KEY")
    subject = os.environ.get("VAPID_SUBJECT", "mailto:owemygod@example.com")
    if private and public:
        app.state.vapid_public = public
        app.state.push_sender = lambda sub, payload: push.send(sub, payload, private, subject)

    @app.on_event("startup")
    async def _start_daily():
        app.state.daily_task = asyncio.create_task(_daily_loop(app))

    @app.on_event("shutdown")
    async def _stop_daily():
        app.state.daily_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await app.state.daily_task

    owner, pw = os.environ.get("OWNER_USERNAME"), os.environ.get("OWNER_PASSWORD")
    if owner and pw and not db.get_user_by_name(app.state.conn, owner):
        db.create_user(app.state.conn, owner, pw, timezone=os.environ.get("OWNER_TIMEZONE", "Asia/Makassar"))
    return app


async def _daily_loop(app: FastAPI, every_seconds: int = 600) -> None:
    """Every 10 minutes: send due morning nudges; hourly: clear demo sandboxes older than 24 h."""
    ticks = 0
    while True:
        try:
            now = app.state.clock()
            if app.state.push_sender:
                await asyncio.to_thread(daily.run_once, app.state.conn, now, app.state.push_sender)
            if ticks % 6 == 0:
                db.delete_old_demo_users(app.state.conn, now.replace(tzinfo=None) - timedelta(hours=24))
        except Exception as e:  # noqa: BLE001  keep the loop alive; the next tick retries
            print(f"[daily] {e!r}")
        ticks += 1
        await asyncio.sleep(every_seconds)

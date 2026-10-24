from datetime import date

from app.views import badge_text, home_rows

MON = date(2026, 10, 19)


def _d(i, name, **kw):
    base = dict(id=i, friend_name=name, currency="IDR", remaining=150_000, amount=150_000, status="open", level=1,
                firm_count=0, rhythm="weekly", rhythm_day=0, next_nudge_on="2026-10-26", promise_on=None,
                last_event=None)
    return {**base, **kw}


SAMPLE = [
    _d(1, "Paid", status="paid"),
    _d(2, "Next", next_nudge_on="2026-10-26"),
    _d(3, "Talk", status="talk"),
    _d(4, "Waiting", promise_on="2026-10-22", next_nudge_on="2026-10-23"),
    _d(5, "Promised", promise_on="2026-10-19", next_nudge_on="2026-10-20"),
    _d(6, "Remind", next_nudge_on="2026-10-18"),
]


def test_home_sort():
    assert [r["badge"] for r in home_rows(SAMPLE, MON)] == ["remind", "promised", "waiting", "next", "talk", "paid"]


def test_badge_texts():
    rows = {r["name"]: r for r in home_rows(SAMPLE, MON)}
    assert badge_text(rows["Remind"]) == "Remind today"
    assert badge_text(rows["Promised"]) == "Promised today"
    assert badge_text(rows["Waiting"]) == "Waiting until Oct 22"
    assert badge_text(rows["Next"]) == "Next: Oct 26"
    assert badge_text(rows["Talk"]) == "Talk in person"
    assert badge_text(rows["Paid"]) == "Paid"


def test_next_within_a_week_shows_weekday():
    r = home_rows([_d(1, "A", next_nudge_on="2026-10-22")], MON)[0]
    assert badge_text(r) == "Next: Thu"


def test_row_fields():
    r = home_rows([_d(1, "budi", last_event={"kind": "excuse", "text": "after payday ya"})], MON)[0]
    assert (r["initial"], r["amount_text"], r["preview"]) == ("B", "Rp150k", '💬 "after payday ya"')

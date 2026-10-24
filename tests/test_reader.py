from datetime import date

from owemygod.reader import Reader
from owemygod.schema import ReplyRead
from tests.fakes import FakeClient

T = date(2026, 10, 23)


def test_reader_uses_model(): assert Reader(FakeClient('{"kind":"vague"}')).read("hmm", T) == (ReplyRead(kind="vague"), "model")
def test_reader_falls_back_on_junk(): assert Reader(FakeClient("lol")).read("besok ya", T)[1] == "rules"
def test_reader_falls_back_on_error(): assert Reader(FakeClient(raises=True)).read("besok ya", T)[1] == "rules"
def test_reader_without_model(): assert Reader(None).read("besok ya", T)[0].when.n == 1


def test_reader_sends_date_and_reply_only():
    fc = FakeClient('{"kind":"vague"}')
    Reader(fc).read("nanti ya", T)
    assert "Today: Friday, 2026-10-23\nReply: nanti ya" in fc.last_prompt

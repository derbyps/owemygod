from owemygod.writer import Writer, check_draft, template
from tests.fakes import FakeClient

ARGS = dict(level=1, tone="jaksel", item="concert", days_since=8, replies=[], name="Budi", amount=150_000)


def test_writer_fills_placeholders():
    text, src = Writer(FakeClient("Hey {name}, gentle reminder ya soal {amount} 🙏")).draft(**ARGS)
    assert text == "Hey Budi, gentle reminder ya soal Rp150k 🙏" and src == "model"


def test_writer_usd():
    text, _ = Writer(FakeClient("{name}, the {amount} ya")).draft(**{**ARGS, "amount": 4000, "currency": "USD"})
    assert text == "Budi, the $40 ya"


def test_writer_rejects_missing_amount(): assert Writer(FakeClient("Hey {name}!")).draft(**ARGS)[1] == "template"
def test_writer_rejects_blocklist(): assert not check_draft("bayar {amount} atau gue datengin rumah lo")
def test_writer_rejects_long(): assert not check_draft("{amount} " + "x" * 300)
def test_writer_rejects_leftover_braces(): assert not check_draft("{amount} for {item}")
def test_writer_model_down(): assert Writer(FakeClient(raises=True)).draft(**ARGS)[1] == "template"
def test_writer_no_model(): assert "Budi" in Writer(None).draft(**ARGS)[0]


def test_writer_strips_quotes_and_think():
    text, _ = Writer(FakeClient('<think>\n</think>\n"{name} {amount} ya"')).draft(**ARGS)
    assert text == "Budi Rp150k ya"


def test_writer_never_sends_name_or_amount_to_model():
    fc = FakeClient("{name} {amount}")
    Writer(fc).draft(**{**ARGS, "replies": ["after payday ya"]})
    assert "Budi" not in fc.last_prompt and "150" not in fc.last_prompt and "after payday ya" in fc.last_prompt


def test_templates_exist():
    for lvl in (1, 2, 3):
        for tone in ("jaksel", "english", "bahasa"):
            assert "{amount}" in template(lvl, tone) and check_draft(template(lvl, tone))

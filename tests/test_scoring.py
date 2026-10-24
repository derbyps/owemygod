from datetime import date

from owemygod.schema import ReplyRead, WhenExpr
from owemygod.scoring import reward, score

T = date(2026, 10, 23)
GOLD = ReplyRead(kind="promise", when=WhenExpr(type="payday"))  # → 2026-10-25


def test_reward_exact(): assert reward('{"kind":"promise","when":{"type":"payday"}}', GOLD, T) == 1
def test_reward_exact_equivalent_expr(): assert reward('{"kind":"promise","when":{"type":"weekday","day":"sun"}}', GOLD, T) == 1
def test_reward_too_early(): assert reward('{"kind":"promise","when":{"type":"relative_days","n":1}}', GOLD, T) == -5
def test_reward_too_late(): assert reward('{"kind":"promise","when":{"type":"month_start"}}', GOLD, T) == -1
def test_reward_wrong_kind(): assert reward('{"kind":"vague"}', GOLD, T) == -2
def test_reward_invalid(): assert reward("nope", GOLD, T) == -5
def test_non_promise_correct(): assert reward('{"kind":"vague"}', ReplyRead(kind="vague"), T) == 1


def test_score_fields():
    s = score(None, GOLD, T)
    assert s == {"valid": False, "kind_ok": False, "exact": False, "early": False, "late": False}

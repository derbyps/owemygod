from datetime import date

from data.gen_dataset import HELDOUT_FAMILIES, TRAIN_FAMILIES, generate
from owemygod.schema import ReplyRead


def test_deterministic():
    assert generate(50, seed=1) == generate(50, seed=1)


def test_targets_valid():
    for r in generate(300, seed=2):
        ReplyRead.model_validate(r["target"])
        date.fromisoformat(r["today"])


def test_heldout_families_excluded_from_train():
    fams = {r["family"] for r in generate(2000, seed=0, families=TRAIN_FAMILIES)}
    assert fams and not fams & HELDOUT_FAMILIES


def test_heldout_covers_every_kind():
    kinds = {r["target"]["kind"] for r in generate(300, seed=1, families=HELDOUT_FAMILIES)}
    assert kinds == {"promise", "vague", "claims_paid"}


def test_kind_mix():
    rows = generate(1000, seed=3)
    share = sum(r["target"]["kind"] == "promise" for r in rows) / len(rows)
    assert 0.63 <= share <= 0.77


def test_code_mixed():
    rows = generate(500, seed=4)
    assert any("ya" in r["reply"] and any(w in r["reply"].lower() for w in ("payday", "next week", "promise"))
               for r in rows)


def test_replies_vary():
    rows = generate(500, seed=5)
    assert len({r["reply"] for r in rows}) > 450


def test_rl_pool_is_separate_from_train_and_test():
    from data.gen_dataset import RL_FAMILIES
    assert RL_FAMILIES and not RL_FAMILIES & TRAIN_FAMILIES and not RL_FAMILIES & HELDOUT_FAMILIES


def test_explicit_date_with_payday_is_labelled_as_the_date():
    rows = [r for r in generate(3000, seed=8) if r["family"] == "pay_date"]
    assert rows and all(r["target"]["when"]["type"] == "day_of_month" for r in rows)


def test_mid_month_is_the_15th():
    rows = [r for r in generate(3000, seed=9) if r["family"] == "mid_month"]
    assert rows and all(r["target"]["when"] == {"type": "day_of_month", "day": 15} for r in rows)


def test_typos_never_touch_digits():
    from data.gen_dataset import _typo
    import random
    rng = random.Random(0)
    for _ in range(500):
        assert "".join(c for c in _typo("tgl 28 ya", rng) if c.isdigit()) == "28"

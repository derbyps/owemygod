"""Synthetic friend replies, generated from their labels (labels are never guessed by an LLM).

Usage:
  python data/gen_dataset.py        # writes data/train.jsonl (2000) and data/test.jsonl (300, held-out phrasings)
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.phrases import COMPOUND, EARLY_BY_TYPE, EMOJI, FAMILIES, FILLERS, OPENERS, PAYDAY_WITH_DATE  # noqa: E402
from owemygod.schema import ReplyRead, WhenExpr, to_target_json  # noqa: E402

HELDOUT_FAMILIES = {name for name, f in FAMILIES.items() if f.get("heldout")}
RL_FAMILIES = {name for name, f in FAMILIES.items() if f.get("rl_only")}
TRAIN_FAMILIES = set(FAMILIES) - HELDOUT_FAMILIES - RL_FAMILIES
KIND_WEIGHTS = {"promise": 0.70, "vague": 0.20, "claims_paid": 0.10}


def _family_kind(f: dict) -> str:
    return f.get("kind", "promise")


def _dom_phrase(style: str, day: int, rng: random.Random) -> str:
    if style == "dom_id":
        return rng.choice([f"tanggal {day}", f"tgl {day}"])
    if style == "dom_short":
        return rng.choice([f"tgl{day}", f"tg {day}", f"{day}an"])
    suffix = "st" if day in (1, 21, 31) else "nd" if day in (2, 22) else "rd" if day in (3, 23) else "th"
    return f"{day}{suffix}"


def _time(f: dict, rng: random.Random) -> tuple[WhenExpr, str]:
    t = f["type"]
    if isinstance(f["times"], str):  # day_of_month styles
        day = rng.randint(1, 31)
        return WhenExpr(type=t, day=day), _dom_phrase(f["times"], day, rng)
    key = rng.choice(list(f["times"]))
    phrase = rng.choice(f["times"][key])
    if t == "relative_days":
        return WhenExpr(type=t, n=key), phrase
    if t == "weekday":
        return WhenExpr(type=t, day=key), phrase
    if t == "day_of_month":
        return WhenExpr(type=t, day=key), phrase
    return WhenExpr(type=t), phrase


def _typo(s: str, rng: random.Random) -> str:
    letters = [i for i, c in enumerate(s) if c.isalpha()]
    if not letters:
        return s
    i = rng.choice(letters)
    if s[i] in "aeiou" and len(s) > 6:
        return s[:i] + s[i + 1:]
    return s[:i] + s[i] + s[i:]


def _decorate(core: str, rng: random.Random) -> str:
    parts = []
    if rng.random() < 0.45:
        parts.append(rng.choice(OPENERS) + ("," if rng.random() < 0.5 else ""))
    parts.append(core)
    if rng.random() < 0.35:
        parts.append(rng.choice(FILLERS))
    text = " ".join(parts)
    if rng.random() < 0.4:
        text += " " + rng.choice(EMOJI)
    if rng.random() < 0.3:
        text = text.capitalize()
    if rng.random() < 0.10:
        text = _typo(text, rng)
    return text.strip()


def _row(i: int, seed: int, name: str, f: dict, rng: random.Random) -> dict:
    today = date(2026, 1, 1) + timedelta(days=rng.randrange(365))
    kind = _family_kind(f)
    if kind == "promise":
        when, phrase = _time(f, rng)
        template = rng.choice(f["templates"])
        core = template.format(t=phrase)
        if when.type == "relative_days" and when.n == 0:
            pass  # nothing earlier than today
        elif rng.random() < 0.25:
            core = rng.choice(COMPOUND).format(early=rng.choice(EARLY_BY_TYPE[when.type]), t=phrase)
        elif when.type == "payday" and rng.random() < 0.25:
            day = rng.choice([1, 5, 10, 15, 25, 28])
            when, core = WhenExpr(type="day_of_month", day=day), rng.choice(PAYDAY_WITH_DATE).format(d=day)
        target = ReplyRead(kind="promise", when=when)
    else:
        core = rng.choice(f["templates"])
        target = ReplyRead(kind=kind)
    return {"id": f"syn-{seed}-{i}", "today": today.isoformat(), "family": name,
            "reply": _decorate(core, rng), "target": json.loads(to_target_json(target))}


def generate(n: int, seed: int, families: set[str] | None = None) -> list[dict]:
    rng = random.Random(seed)
    names = sorted(families if families is not None else TRAIN_FAMILIES | HELDOUT_FAMILIES)
    by_kind: dict[str, list[str]] = {}
    for name in names:
        by_kind.setdefault(_family_kind(FAMILIES[name]), []).append(name)
    kinds = [k for k in KIND_WEIGHTS if k in by_kind]
    weights = [KIND_WEIGHTS[k] for k in kinds]
    rows = []
    for i in range(n):
        name = rng.choice(by_kind[rng.choices(kinds, weights)[0]])
        rows.append(_row(i, seed, name, FAMILIES[name], rng))
    return rows


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    _write(ROOT / "data" / "train.jsonl", generate(2000, seed=0, families=TRAIN_FAMILIES))
    _write(ROOT / "data" / "test.jsonl", generate(300, seed=1, families=HELDOUT_FAMILIES))
    _write(ROOT / "data" / "rl.jsonl", generate(800, seed=2, families=RL_FAMILIES | TRAIN_FAMILIES))

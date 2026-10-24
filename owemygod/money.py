"""Amounts the way people type them: 150k, 150rb, 1,5jt, Rp 150.000, $12.50.

Stored as integers in minor units: rupiah for IDR, cents for USD.
"""
from __future__ import annotations

import re

CURRENCIES = ("IDR", "USD")
MAX_AMOUNT = 10**12
_SUFFIX = {"k": 1_000, "rb": 1_000, "ribu": 1_000, "jt": 1_000_000, "juta": 1_000_000}
_IDR = re.compile(r"^(\d+(?:[.,]\d+)?)(k|rb|ribu|jt|juta)$|^(\d{1,3}(?:[.,]\d{3})+|\d+)$")
_USD = re.compile(r"^(\d+)(?:[.,](\d{1,2}))?$")


def parse_amount(s: str, currency: str = "IDR") -> int:
    t = re.sub(r"\s+", "", s.lower())
    if currency == "USD":
        m = _USD.match(t.lstrip("$"))
        if not m:
            raise ValueError(f"not an amount: {s!r}")
        n = int(m.group(1)) * 100 + int((m.group(2) or "0").ljust(2, "0"))
    else:
        m = _IDR.match(t.removeprefix("rp"))
        if not m:
            raise ValueError(f"not an amount: {s!r}")
        if m.group(2):
            n = round(float(m.group(1).replace(",", ".")) * _SUFFIX[m.group(2)])
        else:
            n = int(re.sub(r"[.,]", "", m.group(3)))
    if n <= 0:
        raise ValueError("amount must be more than zero")
    if n > MAX_AMOUNT:
        raise ValueError("amount is too large")
    return n


def _short(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def format_amount(n: int, currency: str = "IDR") -> str:
    if currency == "USD":
        return f"${n // 100}" if n % 100 == 0 else f"${n / 100:.2f}"
    if n >= 1_000_000:
        return f"Rp{_short(n / 1_000_000)}jt"
    if n >= 1_000:
        return f"Rp{_short(n / 1_000)}k"
    return f"Rp{n}"


def totals(debts: list[dict]) -> str:
    sums = {c: 0 for c in CURRENCIES}
    for d in debts:
        if d["status"] != "paid":
            sums[d["currency"]] += d["remaining"]
    parts = [format_amount(v, c) for c, v in sums.items() if v]
    return " + ".join(parts) or "Rp0"

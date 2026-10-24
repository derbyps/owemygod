"""Indonesian WhatsApp numbers and the official click-to-chat link."""
from __future__ import annotations

import re
from urllib.parse import quote


def normalize(s: str) -> str | None:
    digits = re.sub(r"\D", "", s or "")
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("8"):
        digits = "62" + digits
    return digits if 9 <= len(digits) <= 15 else None


def wa_link(number: str | None, text: str) -> str:
    return f"https://wa.me/{number or ''}?text={quote(text)}"

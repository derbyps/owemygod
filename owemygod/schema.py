"""What the reply reader returns: a kind and, for promises, a date expression (never a date)."""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ValidationError, model_validator

WHEN_TYPES = ("relative_days", "weekday", "next_week", "day_of_month", "payday", "month_start", "month_end")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class ParseError(ValueError):
    pass


class WhenExpr(BaseModel):
    type: Literal["relative_days", "weekday", "next_week", "day_of_month", "payday", "month_start", "month_end"]
    n: int | None = None
    day: str | int | None = None

    @model_validator(mode="after")
    def _check(self) -> "WhenExpr":
        if self.type == "relative_days" and (self.n is None or not 0 <= self.n <= 60):
            raise ValueError("relative_days needs n in 0..60")
        if self.type == "weekday" and self.day not in WEEKDAYS:
            raise ValueError("weekday needs day mon..sun")
        if self.type == "day_of_month" and not (isinstance(self.day, int) and 1 <= self.day <= 31):
            raise ValueError("day_of_month needs day 1..31")
        return self


class ReplyRead(BaseModel):
    kind: Literal["promise", "vague", "claims_paid"]
    when: WhenExpr | None = None

    @model_validator(mode="after")
    def _check(self) -> "ReplyRead":
        if (self.kind == "promise") != (self.when is not None):
            raise ValueError("'when' is required for a promise and only for a promise")
        return self


_THINK = re.compile(r"<think>.*?</think>", re.S)


def parse_reply(text: str) -> ReplyRead:
    text = _THINK.sub("", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ParseError("no JSON object found")
    try:
        return ReplyRead.model_validate(json.loads(text[start:end + 1]))
    except (json.JSONDecodeError, ValidationError) as e:
        raise ParseError(str(e)) from e


def to_target_json(r: ReplyRead) -> str:
    return json.dumps(r.model_dump(exclude_none=True), separators=(",", ":"), ensure_ascii=False)

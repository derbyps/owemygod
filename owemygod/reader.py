"""Read a friend's reply: the fine-tuned model first, keyword rules when it fails."""
from __future__ import annotations

from datetime import date
from typing import Literal

from .prompt import build_reader_messages, render_qwen3_prompt
from .rules import read_by_rules
from .schema import ParseError, ReplyRead, parse_reply


class Reader:
    def __init__(self, client):
        self.client = client

    def read(self, reply: str, today: date) -> tuple[ReplyRead, Literal["model", "rules"]]:
        if self.client is not None:
            try:
                text = self.client.complete(render_qwen3_prompt(build_reader_messages(reply, today)), 80, 0.0)
                return parse_reply(text), "model"
            except (ParseError, Exception):  # noqa: BLE001  model down or unreadable: rules keep the app working
                pass
        return read_by_rules(reply), "rules"

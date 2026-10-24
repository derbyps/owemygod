"""Draft a reminder. The model writes words with {name} and {amount} placeholders; code fills in the
facts, so the model never sees who owes what and can't get the amount wrong."""
from __future__ import annotations

import re
from typing import Literal

from .money import format_amount
from .prompt import render_qwen3_prompt

Tone = Literal["jaksel", "english", "bahasa"]
MAX_LEN = 300
LEVELS = {1: "gentle and warm, almost apologetic for asking",
          2: "playful and teasing, light humour, still friendly",
          3: "firm but kind: clear that you need the money back, no jokes"}
TONES = {"jaksel": "Jakarta-style mix of casual English and Indonesian (\"which is\", \"literally\", \"ya\", \"deh\")",
         "english": "casual English", "bahasa": "casual Indonesian (Bahasa gaul)"}
BLOCKLIST = re.compile(r"\b(datengin|polisi|police|viralin|viral|lapor|sue|lawyer|pengacara|goblok|bego|tolol|"
                       r"anjing|bangsat|kontol|stupid|idiot|loser|kill|bunuh|ancam)\b", re.I)
TEMPLATES: dict[tuple[int, str], str] = {
    (1, "jaksel"): "Hey {name}! Gentle reminder ya soal yang {amount} kemarin 🙏 no pressure tho",
    (2, "jaksel"): "{name}~ which is, the {amount} masih nunggu kamu literally 😆 kabarin ya",
    (3, "jaksel"): "Hi {name}, aku butuh yang {amount} balik ya. Bisa kabarin kapan? Thanks 🙏",
    (1, "english"): "Hey {name}! Just a gentle reminder about the {amount} 🙏 no rush",
    (2, "english"): "{name}, the {amount} misses you 😆 let me know when you can",
    (3, "english"): "Hi {name}, I do need the {amount} back. Can you tell me when? Thanks 🙏",
    (1, "bahasa"): "Halo {name}! Mau ngingetin soal yang {amount} kemarin ya 🙏 santai aja",
    (2, "bahasa"): "{name}, si {amount} kangen pulang nih 😆 kabarin ya",
    (3, "bahasa"): "Halo {name}, aku butuh yang {amount} balik ya. Kira-kira kapan bisa? Makasih 🙏",
}


def template(level: int, tone: Tone) -> str:
    return TEMPLATES[(level, tone)]


def check_draft(text: str) -> bool:
    leftovers = set(re.findall(r"\{(\w+)\}", text)) - {"name", "amount"}
    return "{amount}" in text and len(text) <= MAX_LEN and not leftovers and not BLOCKLIST.search(text)


def build_writer_messages(level: int, tone: Tone, item: str | None, days_since: int,
                          replies: list[str]) -> list[dict[str, str]]:
    system = ("You write one short WhatsApp message to a friend who owes money. Write it as the lender, in "
              f"{TONES[tone]}. Tone: {LEVELS[level]}. Use the placeholders {{name}} and {{amount}} literally; "
              "never invent a name or a number. Max 2 sentences, at most one emoji. No threats, no shaming, "
              "no guilt-tripping. Reply with the message only.")
    facts = [f"It was for: {item}." if item else "", f"Lent {days_since} days ago."]
    if replies:
        facts.append("Their latest replies (newest last): " + " | ".join(f'"{r}"' for r in replies[-2:]) +
                     ". You may refer to them kindly.")
    return [{"role": "system", "content": system}, {"role": "user", "content": " ".join(f for f in facts if f)}]


def _clean(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    return text.strip('"“”').strip()


class Writer:
    def __init__(self, client):
        self.client = client

    def draft(self, *, level: int, tone: Tone, item: str | None, days_since: int, replies: list[str], name: str,
              amount: int, currency: str = "IDR") -> tuple[str, Literal["model", "template"]]:
        text, source = template(level, tone), "template"
        if self.client is not None:
            try:
                prompt = render_qwen3_prompt(build_writer_messages(level, tone, item, days_since, replies))
                out = _clean(self.client.complete(prompt, 120, 0.8))
                if check_draft(out):
                    text, source = out, "model"
            except Exception:  # noqa: BLE001  model down: a template still gets the reminder out
                pass
        return text.replace("{name}", name).replace("{amount}", format_amount(amount, currency)), source

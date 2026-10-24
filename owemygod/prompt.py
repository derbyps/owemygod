"""The one reader prompt used for training, evaluation and serving."""
from __future__ import annotations

from datetime import date

READER_SYSTEM = (
    "You read a friend's reply about when they will pay back money they owe. Replies mix English and "
    "Indonesian (Jakarta slang), with typos and emoji.\n"
    "Classify the reply:\n"
    '- "promise": they give a time. Add "when".\n'
    '- "vague": no time ("nanti ya", "soon", "lagi tight").\n'
    '- "claims_paid": they say they already paid ("udah aku transfer").\n'
    'Never compute a date. Describe the time as one "when" expression:\n'
    '- {"type":"relative_days","n":1}  besok, tomorrow (lusa = 2, today = 0)\n'
    '- {"type":"weekday","day":"fri"}  Jumat, this Friday (mon tue wed thu fri sat sun)\n'
    '- {"type":"next_week"}  minggu depan, next week\n'
    '- {"type":"day_of_month","day":25}  tanggal 25, on the 25th\n'
    '- {"type":"payday"}  abis gajian, after payday\n'
    '- {"type":"month_start"}  awal bulan, early next month\n'
    '- {"type":"month_end"}  akhir bulan, end of the month\n'
    "If several times are mentioned, use the latest one they commit to.\n"
    'Reply with JSON only, e.g. {"kind":"promise","when":{"type":"payday"}} or {"kind":"vague"}.'
)

STOP = ["<|im_end|>"]


def build_reader_messages(reply: str, today: date) -> list[dict[str, str]]:
    return [{"role": "system", "content": READER_SYSTEM},
            {"role": "user", "content": f"Today: {today:%A}, {today.isoformat()}\nReply: {reply}"}]


def render_qwen3_prompt(messages: list[dict[str, str]]) -> str:
    """Exact Qwen3 chat-template string with thinking disabled (matches tinker-cookbook's
    `qwen3_disable_thinking` renderer; verified by train/check_setup.py)."""
    body = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages)
    return body + "<|im_start|>assistant\n<think>\n\n</think>\n\n"

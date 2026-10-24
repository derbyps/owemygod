"""Shared helpers for the Tinker scripts (run on the user's machine, not in CI)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL = "Qwen/Qwen3-8B"
RENDERER = "qwen3_disable_thinking"


def load_jsonl(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def require_api_key() -> None:
    if not os.environ.get("TINKER_API_KEY"):
        sys.exit("TINKER_API_KEY is not set. Run: export TINKER_API_KEY=...  (from the Tinker console)")


def get_tokenizer_and_renderer(model: str = MODEL):
    from tinker_cookbook import renderers
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tokenizer = get_tokenizer(model)
    return tokenizer, renderers.get_renderer(RENDERER, tokenizer)


def response_text(renderer, tokens: list[int]) -> str:
    from tinker_cookbook import renderers

    message, _ = renderer.parse_response(tokens)
    return renderers.get_text_content(message)


def write_result(log_path: str | Path, paths: dict[str, str], extra: dict | None = None) -> Path:
    out = Path(log_path) / "RESULT.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in {**paths, **(extra or {})}.items()]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(["", "=== RESULT ===", *lines, f"(saved to {out})"]))
    return out


class MetricsLog:
    def __init__(self, log_path: str | Path):
        Path(log_path).mkdir(parents=True, exist_ok=True)
        self.f = open(Path(log_path) / "metrics.jsonl", "a", encoding="utf-8")

    def log(self, step: int, **metrics) -> None:
        row = {"step": step, **{k: (round(v, 5) if isinstance(v, float) else v) for k, v in metrics.items()}}
        self.f.write(json.dumps(row) + "\n")
        self.f.flush()
        print(" ".join(f"{k}={v}" for k, v in row.items()))

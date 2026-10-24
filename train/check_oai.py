"""Smoke-test the exact path the web app uses: Tinker's OpenAI-compatible /completions endpoint
with a sampler checkpoint as the model name. Costs < $0.001.

Usage: python train/check_oai.py "tinker://.../sampler_weights/rl-final"
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date

from common import require_api_key  # noqa: F401  (also puts the repo root on sys.path)

from owemygod.model_client import TinkerClient
from owemygod.prompt import build_reader_messages, render_qwen3_prompt
from owemygod.schema import ParseError, parse_reply

REPLY = "besok gabisa bro, jumat aja ya promise"


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].startswith("tinker://"):
        sys.exit(__doc__)
    require_api_key()
    client = TinkerClient(os.environ["TINKER_API_KEY"], sys.argv[1])
    t0 = time.time()
    text = client.complete(render_qwen3_prompt(build_reader_messages(REPLY, date(2026, 10, 21))), 80, 0.0)
    print(f"[ok] endpoint answered in {time.time() - t0:.1f}s:\n{text}")
    try:
        print("[ok] parsed:", parse_reply(text))
        print("\nThe app will work with OWEMYGOD_READER_PATH =", sys.argv[1])
    except ParseError as e:
        sys.exit(f"[fail] output did not parse: {e}")


if __name__ == "__main__":
    main()

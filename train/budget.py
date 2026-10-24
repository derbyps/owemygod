"""Cost estimates for Tinker runs and a hard spending guard.

Prices: USD per 1M tokens, from tinker-docs Models & Pricing (checked 2026-10-16).
"""
from __future__ import annotations

PRICES: dict[str, dict[str, float]] = {
    "Qwen/Qwen3-8B": {"prefill": 0.195, "sample": 0.60, "train": 0.44},
}


def estimate_sft_usd(n_tokens: int, epochs: int, model: str) -> float:
    return n_tokens * epochs * PRICES[model]["train"] / 1e6


def estimate_sample_usd(n_requests: int, prompt_tokens: int, completion_tokens: int, model: str) -> float:
    p = PRICES[model]
    return n_requests * (prompt_tokens * p["prefill"] + completion_tokens * p["sample"]) / 1e6


def estimate_rl_usd(steps: int, batch: int, group: int, prompt_tokens: int, completion_tokens: int,
                    model: str) -> float:
    p = PRICES[model]
    rollouts = steps * batch * group
    per = prompt_tokens * p["prefill"] + completion_tokens * p["sample"] + (prompt_tokens + completion_tokens) * p["train"]
    return rollouts * per / 1e6


def guard(estimate: float, max_usd: float) -> None:
    print(f"[budget] estimated cost ${estimate:.2f} (cap ${max_usd:.2f})")
    if estimate > max_usd:
        print("[budget] over the cap - aborting. Lower the size or raise --max-usd deliberately.")
        raise SystemExit(2)

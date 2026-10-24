"""Client for sampler checkpoints behind Tinker's OpenAI-compatible endpoint."""
from __future__ import annotations

import os

from .prompt import STOP

TINKER_OAI_BASE = "https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1"


class TinkerClient:
    def __init__(self, api_key: str, model_path: str, base_url: str = TINKER_OAI_BASE, timeout: float = 30.0):
        from openai import OpenAI

        self.model_path = model_path
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0)

    def complete(self, prompt: str, max_tokens: int, temperature: float) -> str:
        r = self.client.completions.create(model=self.model_path, prompt=prompt, max_tokens=max_tokens,
                                           temperature=temperature, stop=STOP)
        return r.choices[0].text


def from_env(var: str) -> TinkerClient | None:
    key, path = os.environ.get("TINKER_API_KEY"), os.environ.get(var)
    if not key or not path:
        return None
    return TinkerClient(key, path, base_url=os.environ.get("TINKER_BASE_URL", TINKER_OAI_BASE))

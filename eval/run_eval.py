"""Evaluate rules / base / SFT / RL on the synthetic held-out set and the hand-written set.

Usage:
  python eval/run_eval.py --models rules                        # offline, free
  python eval/run_eval.py --models rules,base,sft,rl \
      --sft-path tinker://.../sampler_weights/sft-final --rl-path tinker://.../sampler_weights/rl-final
Writes eval/out/{results.json,table.md,chart.png}.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "train"))

from eval.report import summarize, write_report  # noqa: E402
from owemygod.rules import read_by_rules  # noqa: E402
from owemygod.schema import ParseError, ReplyRead, parse_reply  # noqa: E402
from owemygod.scoring import score  # noqa: E402

SETS = {"synthetic held-out": ROOT / "data" / "test.jsonl", "hand-written": ROOT / "data" / "handwritten_test.jsonl"}
SET_KEYS = {"test": "synthetic held-out", "handwritten": "hand-written"}
LLM_MODELS = ("base", "sft", "rl")
NAMES = {"rules": "Keyword rules", "base": "Qwen3-8B, untrained", "sft": "Fine-tuned (SFT)", "rl": "Fine-tuned (SFT + RL)"}


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _scored(row: dict, pred: ReplyRead | None, raw: str) -> dict:
    s = score(pred, ReplyRead.model_validate(row["target"]), date.fromisoformat(row["today"]))
    return {"id": row["id"], "reply": row["reply"], "gold": row["target"],
            "pred": pred.model_dump(exclude_none=True) if pred else None, "raw": raw[:500], **s}


def run_rules(rows: list[dict]) -> list[dict]:
    return [_scored(r, read_by_rules(r["reply"]), "") for r in rows]


def run_llm(rows: list[dict], sampler, renderer, max_tokens: int) -> list[dict]:
    import tinker
    from common import response_text

    from owemygod.prompt import build_reader_messages

    params = tinker.types.SamplingParams(max_tokens=max_tokens, temperature=0.0, stop=renderer.get_stop_sequences())
    prompts = [renderer.build_generation_prompt(build_reader_messages(r["reply"], date.fromisoformat(r["today"])))
               for r in rows]
    futures = [sampler.sample(prompt=p, num_samples=1, sampling_params=params) for p in prompts]
    out = []
    for row, fut in zip(rows, futures):
        try:  # one failed request must not throw away a paid run
            text = response_text(renderer, fut.result().sequences[0].tokens)
        except Exception as e:  # noqa: BLE001
            out.append(_scored(row, None, f"ERROR: {e!r}"))
            continue
        try:
            pred = parse_reply(text)
        except ParseError:
            pred = None
        out.append(_scored(row, pred, text))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default="rules,base,sft,rl")
    ap.add_argument("--sets", default="test,handwritten")
    ap.add_argument("--sft-path")
    ap.add_argument("--rl-path")
    ap.add_argument("--max-tokens", type=int, default=80)
    ap.add_argument("--max-usd", type=float, default=0.3)
    ap.add_argument("--out", default=str(ROOT / "eval" / "out"))
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    sets = {SET_KEYS[s]: _load(SETS[SET_KEYS[s]]) for s in args.sets.split(",")}
    sets = {k: v for k, v in sets.items() if v}
    if not sets:
        sys.exit("No test rows found. Run python data/gen_dataset.py (and fill data/handwritten_test.jsonl).")
    llms = [m for m in models if m in LLM_MODELS]
    for m, p in (("sft", args.sft_path), ("rl", args.rl_path)):
        if m in llms and not p:
            sys.exit(f"--{m}-path is required to evaluate '{m}'")

    rows_out: dict[str, dict[str, list]] = {s: {} for s in sets}
    out_dir = Path(args.out)

    def save() -> None:
        write_report({s: {NAMES[m]: summarize(r) for m, r in d.items()} for s, d in rows_out.items()}, out_dir)
        (out_dir / "results.json").write_text(json.dumps(rows_out, ensure_ascii=False, indent=1), encoding="utf-8")

    if "rules" in models:
        for s, rows in sets.items():
            rows_out[s]["rules"] = run_rules(rows)

    if llms:
        from budget import estimate_sample_usd, guard
        from common import MODEL, get_tokenizer_and_renderer, require_api_key

        n_req = len(llms) * sum(len(v) for v in sets.values())
        guard(estimate_sample_usd(n_req, 520, 30, MODEL), args.max_usd)
        require_api_key()
        import tinker

        _tok, renderer = get_tokenizer_and_renderer()
        service = tinker.ServiceClient()
        paths = {"base": None, "sft": args.sft_path, "rl": args.rl_path}
        for m in llms:
            sampler = (service.create_sampling_client(base_model=MODEL) if m == "base"
                       else service.create_sampling_client(model_path=paths[m]))
            for s, rows in sets.items():
                t0 = time.time()
                rows_out[s][m] = run_llm(rows, sampler, renderer, args.max_tokens)
                sm = summarize(rows_out[s][m])
                print(f"[{m}] {s}: exact {sm['exact']:.1%} early {sm['early']:.1%} valid {sm['valid']:.0%} "
                      f"({time.time() - t0:.0f}s)")
                save()  # paid results survive a later failure

    save()
    print((out_dir / "table.md").read_text(encoding="utf-8"))
    print(f"Report written to {out_dir}")


if __name__ == "__main__":
    main()

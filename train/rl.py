"""Stage 2: reinforcement learning with an asymmetric reward, on Tinker.

Reward per sampled reply reading (owemygod/scoring.py):
  +1 the resolved date is exactly right (or the kind is right for vague / claims_paid)
  -1 the date is too late (you nudge a few days late)
  -5 the date is too early (you nudge before the promised day: rude, costs a friendship)
  -2 wrong kind, -5 output that isn't valid JSON.

Usage:
  python train/rl.py --from-state tinker://.../sft-final --dry-run
  python train/rl.py --from-state tinker://.../sft-final
"""
from __future__ import annotations

import argparse
import random
import time
from datetime import date

from budget import estimate_rl_usd, guard
from common import MODEL, ROOT, MetricsLog, get_tokenizer_and_renderer, load_jsonl, require_api_key, response_text, write_result

from owemygod.prompt import build_reader_messages
from owemygod.schema import ParseError, ReplyRead, parse_reply, to_target_json
from owemygod.scoring import reward, score


def _messages(row: dict) -> list[dict]:
    return build_reader_messages(row["reply"], date.fromisoformat(row["today"]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-state", required=True, help="state_path printed by train/sft.py")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--data", default=str(ROOT / "data" / "rl.jsonl"))
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--batch", type=int, default=32, help="replies per step")
    ap.add_argument("--group", type=int, default=4, help="samples per reply")
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-tokens", type=int, default=80)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--max-usd", type=float, default=1.2)
    ap.add_argument("--save-every", type=int, default=5)
    ap.add_argument("--log-path", default=str(ROOT / "runs" / "rl"))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tokenizer, renderer = get_tokenizer_and_renderer(args.model)
    rows = load_jsonl(args.data)
    rng = random.Random(args.seed)
    probe = rng.sample(rows, min(200, len(rows)))
    prompt_tok = sum(renderer.build_generation_prompt(_messages(r)).length for r in probe) / len(probe)
    compl_tok = 1.15 * sum(len(tokenizer.encode(to_target_json(ReplyRead.model_validate(r["target"]))))
                           for r in probe) / len(probe)
    print(f"[data] mean prompt {prompt_tok:.0f} tokens, mean completion ~{compl_tok:.0f} tokens")
    guard(estimate_rl_usd(args.steps, args.batch, args.group, int(prompt_tok), int(compl_tok), args.model),
          args.max_usd)
    if args.dry_run:
        print("[dry-run] nothing was sent to Tinker.")
        return

    require_api_key()
    import tinker
    import torch
    from tinker import types
    from tinker.types.tensor_data import TensorData
    from tinker_cookbook import checkpoint_utils

    service = tinker.ServiceClient()
    tc = service.create_training_client_from_state(args.from_state)
    params = types.SamplingParams(max_tokens=args.max_tokens, temperature=args.temperature,
                                  stop=renderer.get_stop_sequences())
    adam = types.AdamParams(learning_rate=args.lr, beta1=0.9, beta2=0.95, eps=1e-8)
    log = MetricsLog(args.log_path)

    for step in range(args.steps):
        t0 = time.time()
        if args.save_every and step > 0 and step % args.save_every == 0:
            checkpoint_utils.save_checkpoint(training_client=tc, name=f"rl-{step:03d}", log_path=args.log_path,
                                             kind="sampler", loop_state={"step": step}, ttl_seconds=None)
        sampler = tc.save_weights_and_get_sampling_client()
        batch = rng.sample(rows, args.batch)
        prompts = [renderer.build_generation_prompt(_messages(r)) for r in batch]
        futures = [sampler.sample(prompt=p, num_samples=args.group, sampling_params=params) for p in prompts]

        datums, rewards, exact, early, invalid = [], [], 0, 0, 0
        for fut, prompt, row in zip(futures, prompts, batch):
            gold, today = ReplyRead.model_validate(row["target"]), date.fromisoformat(row["today"])
            seqs = fut.result().sequences
            group_rewards = []
            for seq in seqs:
                text = response_text(renderer, seq.tokens)
                group_rewards.append(reward(text, gold, today))
                try:
                    s = score(parse_reply(text), gold, today)
                    exact += s["exact"]
                    early += s["early"]
                except ParseError:
                    invalid += 1
            rewards += group_rewards
            mean = sum(group_rewards) / len(group_rewards)
            advantages = [r - mean for r in group_rewards]
            if all(a == 0.0 for a in advantages):
                continue
            for seq, adv in zip(seqs, advantages):
                ob_len = prompt.length - 1
                model_input = prompt.append(types.EncodedTextChunk(tokens=seq.tokens[:-1]))
                target = [0] * ob_len + list(seq.tokens)
                logprobs = [0.0] * ob_len + list(seq.logprobs)
                advs = [0.0] * ob_len + [adv] * (model_input.length - ob_len)
                datums.append(types.Datum(model_input=model_input, loss_fn_inputs={
                    "target_tokens": TensorData.from_torch(torch.tensor(target)),
                    "logprobs": TensorData.from_torch(torch.tensor(logprobs)),
                    "advantages": TensorData.from_torch(torch.tensor(advs)),
                }))
        if datums:
            fb = tc.forward_backward(datums, loss_fn="importance_sampling")
            opt = tc.optim_step(adam)
            fb.result()
            opt.result()
        n = len(rewards)
        log.log(step, reward=sum(rewards) / n, exact_rate=exact / n, early_rate=early / n,
                invalid_rate=invalid / n, trained_on=len(datums), secs=round(time.time() - t0, 1))

    paths = checkpoint_utils.save_checkpoint(training_client=tc, name="rl-final", log_path=args.log_path,
                                             kind="both", loop_state={"step": args.steps}, ttl_seconds=None)
    write_result(args.log_path, paths)
    print("\nNext: python eval/run_eval.py --sft-path <sft sampler_path> --rl-path <sampler_path above>")


if __name__ == "__main__":
    main()

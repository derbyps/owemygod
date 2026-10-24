"""Stage 1: supervised fine-tuning (LoRA) of Qwen3-8B on friend replies, on Tinker.

Usage:
  python train/sft.py --dry-run        # count tokens + show cost, spend nothing
  python train/sft.py                  # train (default cap $1.00)
Prints state_path / sampler_path at the end and writes runs/sft/RESULT.txt.
"""
from __future__ import annotations

import argparse
import random
import time
from datetime import date

from budget import estimate_sft_usd, guard
from common import MODEL, ROOT, MetricsLog, get_tokenizer_and_renderer, load_jsonl, require_api_key, write_result

from owemygod.prompt import build_reader_messages
from owemygod.schema import ReplyRead, to_target_json


def build_datums(rows: list[dict], renderer, max_length: int):
    from tinker_cookbook import renderers
    from tinker_cookbook.supervised.data import conversation_to_datum

    datums = []
    for r in rows:
        target = to_target_json(ReplyRead.model_validate(r["target"]))
        convo = build_reader_messages(r["reply"], date.fromisoformat(r["today"])) + [
            {"role": "assistant", "content": target}]
        datums.append(conversation_to_datum(convo, renderer, max_length,
                                            renderers.TrainOnWhat.LAST_ASSISTANT_MESSAGE))
    return datums


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--data", default=str(ROOT / "data" / "train.jsonl"))
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=None, help="default: tinker_cookbook.hyperparam_utils.get_lr")
    ap.add_argument("--lora-rank", type=int, default=32)
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--max-usd", type=float, default=1.0)
    ap.add_argument("--log-path", default=str(ROOT / "runs" / "sft"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from tinker_cookbook.hyperparam_utils import get_lr

    lr = args.lr or get_lr(args.model)
    _tok, renderer = get_tokenizer_and_renderer(args.model)
    rows = load_jsonl(args.data)
    datums = build_datums(rows, renderer, args.max_length)
    n_tokens = sum(d.model_input.length for d in datums)
    print(f"[data] {len(datums)} examples, {n_tokens:,} tokens/epoch, lr={lr:.2e}")
    guard(estimate_sft_usd(n_tokens, args.epochs, args.model), args.max_usd)
    if args.dry_run:
        print("[dry-run] nothing was sent to Tinker.")
        return

    require_api_key()
    import tinker
    from tinker_cookbook import checkpoint_utils
    from tinker_cookbook.supervised.common import compute_mean_nll

    service = tinker.ServiceClient()
    tc = service.create_lora_training_client(base_model=args.model, rank=args.lora_rank)
    log = MetricsLog(args.log_path)
    steps_per_epoch = len(datums) // args.batch_size
    total = steps_per_epoch * args.epochs
    rng = random.Random(args.seed)
    step = 0
    for epoch in range(args.epochs):
        order = list(range(len(datums)))
        rng.shuffle(order)
        for b in range(steps_per_epoch):
            t0 = time.time()
            batch = [datums[i] for i in order[b * args.batch_size:(b + 1) * args.batch_size]]
            cur_lr = lr * max(0.0, 1.0 - step / total)
            fb = tc.forward_backward(batch, loss_fn="cross_entropy")
            opt = tc.optim_step(tinker.AdamParams(learning_rate=cur_lr, beta1=0.9, beta2=0.95, eps=1e-8))
            res = fb.result()
            opt.result()
            nll = compute_mean_nll([x["logprobs"] for x in res.loss_fn_outputs],
                                   [d.loss_fn_inputs["weights"] for d in batch])
            log.log(step, epoch=epoch, train_nll=float(nll), lr=cur_lr, secs=round(time.time() - t0, 1),
                    progress=f"{step + 1}/{total}")
            step += 1

    paths = checkpoint_utils.save_checkpoint(training_client=tc, name="sft-final", log_path=args.log_path,
                                             kind="both", loop_state={"step": step}, ttl_seconds=None)
    write_result(args.log_path, paths)
    print("\nNext: python train/rl.py --from-state <state_path above>")


if __name__ == "__main__":
    main()

"""Pre-flight check before spending money. Costs < $0.001.

1. TINKER_API_KEY is set
2. Our hand-written serving prompt equals the cookbook renderer's prompt byte-for-byte
3. One sample from the base model succeeds
With --save-base: also saves the untrained LoRA as a sampler checkpoint and prints its path.
That path is OWEMYGOD_WRITER_PATH: the reminder writer uses the base model, not the reader adapter.

Usage: python train/check_setup.py [--save-base]
"""
from __future__ import annotations

import argparse
from datetime import date

from common import MODEL, ROOT, get_tokenizer_and_renderer, require_api_key, response_text, write_result

from owemygod.prompt import build_reader_messages, render_qwen3_prompt
from owemygod.schema import ParseError, parse_reply

REPLY = "sorry bgt, abis gajian ya literally langsung 🙏"
TODAY = date(2026, 10, 23)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--save-base", action="store_true")
    args = ap.parse_args()
    require_api_key()
    import tinker

    tokenizer, renderer = get_tokenizer_and_renderer()
    messages = build_reader_messages(REPLY, TODAY)
    model_input = renderer.build_generation_prompt(messages)
    rendered = tokenizer.decode(model_input.to_ints())
    ours = render_qwen3_prompt(messages)
    if rendered != ours:
        print("PROMPT MISMATCH\n--- cookbook ---\n" + repr(rendered) + "\n--- ours ---\n" + repr(ours))
        raise SystemExit(1)
    print(f"[ok] serving prompt matches cookbook renderer ({model_input.length} tokens)")

    service = tinker.ServiceClient()
    sampler = service.create_sampling_client(base_model=MODEL)
    params = tinker.types.SamplingParams(max_tokens=80, temperature=0.0, stop=renderer.get_stop_sequences())
    res = sampler.sample(prompt=model_input, num_samples=1, sampling_params=params).result()
    text = response_text(renderer, res.sequences[0].tokens)
    print("[ok] base model replied:\n" + text)
    try:
        print("[ok] parsed:", parse_reply(text))
    except ParseError as e:
        print("[note] base model output did not parse (that's what fine-tuning fixes):", e)

    if args.save_base:
        from tinker_cookbook import checkpoint_utils

        tc = service.create_lora_training_client(base_model=MODEL, rank=32)
        log_path = ROOT / "runs" / "base"
        paths = checkpoint_utils.save_checkpoint(training_client=tc, name="base-writer", log_path=str(log_path),
                                                 kind="sampler", loop_state={"step": 0}, ttl_seconds=None)
        write_result(log_path, paths)
        print("Set OWEMYGOD_WRITER_PATH to the sampler_path above.")
    print("\nSetup looks good. Next: python train/sft.py --dry-run")


if __name__ == "__main__":
    main()

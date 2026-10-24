# Runbook: train, evaluate and deploy OweMyGod

Total [Tinker](https://thinkingmachines.ai/tinker/) spend for everything we ran was about **$2.40**. Every paid script prints its cost
estimate first and refuses to run above its cap.

## 0. Setup (≈3 min)

Tinker needs Python 3.11 or newer.

```bash
cd owemygod
python3.12 -m venv .venv && source .venv/bin/activate     # or: uv venv -p 3.12 .venv
pip install -r requirements-train.txt
export TINKER_API_KEY=tml-...                              # from the Tinker console
pytest -q                                                  # every test should pass
python data/gen_dataset.py                                 # 2,000 training + 300 held-out replies
```

## 1. Pre-flight and the writer model (< $0.01)

```bash
python train/check_setup.py --save-base
```

Checks the key, checks that the app's prompt matches the training prompt byte for byte, samples one answer from
the untrained model, and saves the untrained model as a sampler checkpoint. Its `sampler_path` (also in
`runs/base/RESULT.txt`) is `OWEMYGOD_WRITER_PATH`: reminders are written by the base model, not by the reader.

## 2. SFT (≈ $0.61, 15–30 min)

```bash
python train/sft.py --dry-run
python train/sft.py --log-path runs/sft2   # the shipped model; paths saved in runs/sft2/RESULT.txt
```

## 3. RL with the "never too early" reward (≈ $0.58, 20–40 min)

```bash
python train/rl.py --from-state "<state_path from step 2>" --log-path runs/rl2 --dry-run
python train/rl.py --from-state "<state_path from step 2>" --log-path runs/rl2
```

Optional. In our runs the SFT model answered every RL-pool reply identically and correctly, so `trained_on` stayed
0 and RL changed nothing; we stopped it and ship SFT. Watch `trained_on` in the first steps before paying for more.

## 4. Evaluation (≈ $0.05)

`data/handwritten_dev.jsonl` (50) found the failure patterns; `data/handwritten_test.jsonl` (25) was written afterwards and run once.

```bash
python eval/run_eval.py --models rules,base,sft --sets handwritten,dev,test --sft-path "<runs/sft2 sampler_path>"
```

Writes `eval/out/table.md`, `chart.png` and `results.json`.

## 5. Check the path the app uses (< $0.001)

```bash
python train/check_oai.py "<runs/sft2 sampler_path>"
```

## 6. Deploy on Render

1. Push to GitHub. On render.com: **New → Blueprint**, pick the repo (it reads `render.yaml`: Starter instance
   plus a 1 GB disk for the SQLite file).
2. Generate push keys: `python scripts/gen_vapid.py`.
3. Set the environment variables: `TINKER_API_KEY`, `OWEMYGOD_READER_PATH` (runs/sft2 sampler_path),
   `OWEMYGOD_WRITER_PATH` (base sampler_path), `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
   `VAPID_SUBJECT` (`mailto:you@example.com`), `OWNER_USERNAME`, `OWNER_PASSWORD`.
   Optional limits: `OWEMYGOD_DEMO_MODEL_CALLS_PER_HOUR` (default 20), `OWEMYGOD_MODEL_CALLS_PER_DAY` (500).
4. Open `<url>/healthz`: it should say `"reader": true, "writer": true`.
5. On your phone: open the site, install it (Android: Chrome menu → Install app; iPhone: Safari → Share → Add to
   Home Screen, then open it from the home screen), go to Settings → **Turn on notifications** → **Send a test
   notification**.

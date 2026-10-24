# OweMyGod

**Chasing friend debts slowly, which is the only way to stay friends.**

A small web app for the friend who always lends and never gets paid back. It keeps a list of who owes you, reads
their replies ("after payday ya", "besok gabisa, jumat aja"), drafts a gentle-to-firm WhatsApp reminder at the
right moment, and nudges you once at 09:00 when someone is due.

Built for the DEV × Hacktoberfest 2026 Open-Source AI Challenge, week 3: *Slow and Steady*.

## Who it's for

People in Jakarta who lend money to friends and hate chasing it. In Indonesia there is even a saying for it:
*yang ngutang lebih galak*, the borrower gets more offended than the lender. OweMyGod does the remembering and the
awkward wording; you only press send.

- **A chat-list home**: who owes you, how much, and who is due today (bold, like an unread chat).
- **Replies become dates**: log what they said and the app works out when to remind next. "Abis gajian" waits for
  payday; "minggu depan" waits for Monday.
- **Reminders that escalate slowly**: gentle, then playful, then firm, never two within 3 days, and after three
  firm ones with no answer it says "talk in person" and stops.
- **Open in WhatsApp**: the draft opens in WhatsApp with the text filled in; you press send. No unofficial bots.
- **One push at 09:00**, Android and iPhone, only when something is due.
- **Rp and $**, English UI, reminders in Jaksel English–Indonesian mix, plain English or Bahasa.

## How it works

```
"sorry bgt, abis gajian ya"  ─►  fine-tuned Qwen3-8B  ─►  {"kind":"promise","when":{"type":"payday"}}
                                   (reads, never counts)              │
                                                                     ▼
                                                    code: payday = the 25th → Oct 25
                                                    code: remind Oct 26 if not paid, one level firmer

level + tone + their replies ─► Qwen3-8B ─► "Hey {name}, udah gajian kan? 😄 the {amount} ya"
                                              code fills in name and amount
```

1. **The model translates; code decides.** The reader only names the *kind* of time ("payday", "next week",
   "the 25th"). Plain Python turns it into a date and runs the schedule, so the model can't miscount a calendar.
2. **Never too early.** "Too early" is the metric that matters: a reminder before the promised day is the one that
   costs a friendship. The RL reward was built around it (−5 too early, −1 late); see Results for what happened.
3. **The model never sees who owes what.** Names, phone numbers and amounts stay in the app's database; the
   writer works with `{name}` and `{amount}` placeholders.
4. **It still works when the model is down**: keyword rules read replies and templates write reminders, and the
   screen says so.

## Results

The real test is **25 replies written by hand by two people** (fictional names), never seen during training and
evaluated once, at the end. "Too early" means the app would remind your friend before the day they promised.

| System | Exact date ↑ | Too early ↓ | Kind right ↑ |
|---|---|---|---|
| Keyword rules | 60% | 16% | 84% |
| Qwen3-8B, untrained | 68% | 12% | 80% |
| **Qwen3-8B fine-tuned on Tinker (shipped)** | **92%** | **8%** | **100%** |

Both remaining misses are one day early: *"tgl 25 pas payday… eh tgl 25 minggu kan? senin deh"* (it kept the 25th)
and *"tgl 28/29"* (it picked the 28th).

How we got there, honestly:

- **v1** was trained on 2,000 synthetic replies. On a first hand-written set of 50 (the *dev set*) it still reminded
  too early 14% of the time, mostly by choosing "payday" when the friend had named a date (*"tgl 28 ya pas payday"*).
- **v2** fixed the generator for the patterns the dev set exposed (an explicit date beats payday, mid-month is the
  15th, "tar malam" is today) and was retrained. Only then was the separate 25-reply test written and run.
- **RL found nothing left to fix.** Reinforcement learning with a −5 penalty for "too early" ran twice, but the
  SFT model answered every training reply identically and correctly, so there was no signal (`trained_on=0`, see
  `runs/rl*/metrics.jsonl`). We ship SFT v2 and say so.

Full tables (synthetic held-out, dev and test, including v1): [`eval/out/table.md`](eval/out/table.md). Total Tinker
spend ≈ $2.40. Reproduce with [RUNBOOK.md](RUNBOOK.md).

## Run it

```bash
pip install -r requirements-app.txt
OWNER_USERNAME=me OWNER_PASSWORD=pw uvicorn app.main:app_from_env --factory --reload
# open http://127.0.0.1:8000 (rules + templates mode without Tinker keys)
pytest -q
```

Training, evaluation and deployment, step by step with costs: [RUNBOOK.md](RUNBOOK.md). Deploys to Render with
[`render.yaml`](render.yaml).

## What's where

| Path | What |
|---|---|
| `owemygod/` | Reply schema, date resolver, schedule, rules, reader, writer, money, SQLite, push |
| `app/` | FastAPI app, templates, the kasbon-book CSS, service worker |
| `data/` | Synthetic reply generator and the hand-written test set |
| `train/` | Tinker SFT and RL scripts with cost guards |
| `eval/` | Evaluation and report |

## Data and licences

- Code: MIT.
- Model: [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B), Apache-2.0, fine-tuned with LoRA on Tinker.
- Training data is synthetic and generated from its labels; no real chats were used.

**Privacy:** names, phone numbers and amounts live only in the app's SQLite file. The text of logged replies is
sent to Tinker's inference endpoint to be read. The public demo uses fictional people.

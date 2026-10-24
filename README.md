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
2. **Never too early.** Training uses reinforcement learning with a lopsided reward: reminding someone *before* the
   day they promised costs −5, reminding late costs −1. A too-early reminder is the one that costs a friendship.
3. **The model never sees who owes what.** Names, phone numbers and amounts stay in the app's database; the
   writer works with `{name}` and `{amount}` placeholders.
4. **It still works when the model is down**: keyword rules read replies and templates write reminders, and the
   screen says so.

## Results

Measured on held-out replies the model never saw: a synthetic set built from held-out phrasings, and a set of
replies written by hand by real people (fictional names). Full table: [`eval/out/table.md`](eval/out/table.md);
reproduce with [RUNBOOK.md](RUNBOOK.md).

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

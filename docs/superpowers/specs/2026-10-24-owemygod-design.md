# OweMyGod — Design Spec

Date: 2026-10-24 · Challenge: DEV Hacktoberfest Open-Source AI Challenge, Week 3 "Slow and Steady"
Deadline: 2026-10-25 23:59 PDT (= 2026-10-26 13:59 WIB / 14:59 WITA)

> *OweMyGod: chasing friend debts slowly, which is the only way to stay friends.*

## 1. Intent

**What the user said**
- A friend keeps lending money and hates chasing it. The friend liked the idea (iPhone user); the author tests on Android.
- A **web app**, not a chat bot: a **list of friends who owe you**. A row looks **"unread"** on the day you should follow up.
- A **D-1 reminder** so you don't forget who is due tomorrow, as a **push notification** on the phone (Android and iPhone).
- A **"Send now"** button. Sending must be legal and seamless: no unofficial WhatsApp automation.
- The friend's **reply** (excuse) is logged as a short note ("lagi buat beli susu, katanya minggu depan"). Logged replies refine the *next* reminder: its date and its wording. This is a log, **not a chatbot**.
- The detail page reads like a **log** (a tracking timeline), never chat bubbles.
- The daily push arrives at **09:00 WITA** for the author.
- Home looks like a **chat list** (WhatsApp-style rows with unread badges) with a **+** button; a new debt needs only name, amount and an optional due date.
- Reminders follow a **rhythm** (e.g. weekly on Monday). A logged promise ("Friday ya") brings a push on that day: "Budi promised to pay today". A **Remind now** button drafts a message any day.
- **Not an AI-looking UI**; use the author's brand colors.
- **English UI**: the target user is a South Jakarta ("Jaksel") English-Indonesian speaker.
- Why open matters: friends' phone numbers and money excuses are personal; they should not go to a general AI assistant.

**Assumptions (flag if wrong)**
- "Send now" (labelled **Open in WhatsApp**) opens WhatsApp's official click-to-chat link with the text prefilled; the user presses send. The app then records the nudge.
- Single real user (the author) behind a password. Judges use per-visitor demo sandboxes.
- Push is the only notification channel; no email.

**Success criteria**
- Live demo on Render; public GitHub repo; DEV post published before the deadline.
- Fine-tuned Qwen3-8B reads excuses measurably better than its base model and a regex baseline. Headline metric: **too-early nudge rate** (nudging before the date the friend promised).
- Push works on Android Chrome and on iPhone (home-screen web app, iOS 16.4+).
- Tinker spend ≤ $3 (hard cap in scripts); $1 kept in reserve. Render spend ≈ $7/month.

**Prize categories targeted:** Overall, **Tinker (primary)**, **Render** (web service + disk + in-app scheduler + Tinker endpoint). Backboard dropped: the database already holds each friend's history, so it would be forced.

**Execution constraint (same as BoldPrint):** Tinker's API is not reachable from Claude's sandboxes. Claude writes all code and tests; the user runs the Tinker-touching commands (SFT, RL, eval, endpoint check) in their own terminal and shares the output.

## 2. Decisions

| Decision | Choice | Why |
|---|---|---|
| Base model | Qwen3-8B on Tinker, non-thinking mode | Cheapest small model on Tinker (prefill $0.195, sample $0.60, train $0.44 per M, checked 2026-10-16); proven in BoldPrint |
| Training | SFT, then RL with an asymmetric reward | Nudging too early costs a friendship; too late only costs time |
| Inference | Tinker OpenAI-compatible endpoint, sampler checkpoint path | No GPU hosting; beta/low traffic fits a single-user app |
| Model's jobs | (1) read an excuse into a *date expression*; (2) write a nudge with placeholders | The model translates, code counts and decides |
| Hosting | Render Starter web service ($7) + 1 GB disk | Doesn't sleep, so the scheduler runs in-process; a disk can only attach to one service |
| Database | SQLite on the Render disk | Same machine as the app; no separate database bill |
| Push | Web Push (VAPID) via `pywebpush`; PWA manifest + service worker | One standard for Android and iOS 16.4+ |
| Sending | `https://wa.me/<number>?text=…` (demo: `https://wa.me/?text=…`) | Official, legal; the user presses send |
| UI | FastAPI + server-rendered HTML + a little vanilla JS, mobile-first | Small, fast to build, installable as a PWA |
| Language | English UI; excuses and nudges in Jaksel code-mix (tone options: Jaksel mix / English / Bahasa) | Matches the target user; code-mixed casual tone is where a model beats templates |
| Money format | Currency per debt: `IDR` → `Rp150k`, `Rp1.2jt`; `USD` → `$40`, `$12.50`. Stored as integer minor units (rupiah / cents) | How the target user writes it; Rp and $ only for now |

## 3. What the model does vs. what code does

### 3.1 Excuse reader (fine-tuned)

Input: the excuse text and today's date with weekday. **No names, numbers or amounts are sent.**

Output (JSON, validated with pydantic):

```json
{"kind": "promise", "when": {"type": "payday"}}
```

- `kind`: `promise` (gives a time), `vague` ("nanti ya", "soon"), `claims_paid` ("udah aku transfer kok").
- `when` (only for `promise`), one of:
  - `{"type": "relative_days", "n": 1}`: besok, tomorrow, lusa (2)
  - `{"type": "weekday", "day": "fri"}`: Jumat, this Friday
  - `{"type": "next_week"}`: minggu depan, next week
  - `{"type": "day_of_month", "day": 25}`: tanggal 25, on the 25th
  - `{"type": "payday"}`: abis gajian, after payday
  - `{"type": "month_start"}` / `{"type": "month_end"}`: awal bulan / akhir bulan

**Code resolves** the expression to a calendar date (`resolve.py`): `next_week` → Monday of next week; `payday` → the friend's payday setting (default 25th) or the next one if passed; `month_start` → the 1st of next month; `day_of_month` → the next occurrence. All dates in the user's timezone.

`claims_paid` never marks a debt paid; it shows "They say they've paid. Check your bank?" with a **Paid** button.

### 3.2 Nudge writer (base model, no fine-tune)

Input: escalation level (1 gentle, 2 playful, 3 firm), tone, what the money was for, days since the loan, and the **last 2 logged replies** with how they were read (so the next message can refer to them: "udah gajian kan? 😄"). Output: one message using placeholders `{name}` and `{amount}`; code fills them in.

Guards (code): must contain `{amount}`; ≤ 300 characters; a blocklist of threats and insults; otherwise use a fixed template for that level and tone. If the model is unreachable, templates are used and the UI says so.

### 3.3 Schedule (code only)

Each debt has a **reminder rhythm**, chosen when it's created (default from Settings: weekly on Monday):
`weekly on <day>` · `every 2 weeks on <day>` · `monthly on <date>` (e.g. the 25th, payday).

- **First reminder:** the due date if one was given; otherwise the next rhythm day.
- **On a rhythm day:** a reminder is due. Each sent reminder raises the tone one level: gentle → playful → firm (stays firm).
- **Reply with a promise** (e.g. logged Wednesday: "Friday ya"): the rhythm pauses until that date.
  - On the promise day the push says **"Budi promised to pay today (Rp150k)"**. No message is drafted that day; it's a heads-up.
  - If the debt isn't marked paid by the next morning, a reminder is due that day ("Budi's promise was yesterday"), one level up. Then the normal rhythm resumes.
- **Vague reply** ("nanti ya"): the rhythm continues unchanged; the reply is still used to write the next message.
- **Remind now** (button, any day — e.g. you saw Budi posting concert photos on Friday): drafts a message immediately at the current level. Sending it counts as a reminder, and the next rhythm day is **skipped if it falls within 3 days** (Friday → Sunday is skipped; the next one is the Sunday after). Slow and steady: never two reminders in 3 days.
- **After 3 firm reminders with no payment or reply:** status **"Talk in person"**, reminders stop, with a **Resume reminders** button.
- **Partial payment** lowers the remaining amount; the rhythm continues.
- **Paid** ends everything.

### 3.4 Daily job (in-process)

An asyncio task checks every 10 minutes; once per day after **09:00 in the user's timezone** (author: Asia/Makassar, WITA; default Asia/Jakarta) it sends **one** push summarising the day, e.g.:
"Remind today: Sari, Andi · Budi promised to pay today". If nothing is due, no push. A `push_log(user_id, date)` row makes it idempotent across restarts.

## 4. Screens (English UI, mobile-first)

1. **Home: a chat-list look** (like WhatsApp's list of chats — familiar, *not* a chatbot):
   - Header: "You're owed Rp1.25jt · $40" (one total per currency).
   - Each row: an initial avatar, name, amount, and a one-line preview of the latest log entry (`💬 "after payday ya"`, `📤 Reminder sent Mon`); on the right, the date and a badge.
   - **Unread style = action needed today**: bold row + yellow dot (*Remind today*) or orange badge (*Promised today*). Other states: *Waiting until Oct 25*, *Next: Mon*, *Talk in person*; *Paid* rows are grey at the bottom.
   - Sorted: action today first, then by next date; paid last.
   - A floating **+** button to add a debt.
2. **New debt** (one short form): **name**, **amount** with a currency dropdown **Rp / $** (Rp accepts "150k", "1.2jt"; $ accepts "12.5", "$40"), **due date (optional)**. Optional, collapsed under "More": WhatsApp number (if empty, *Open in WhatsApp* lets you pick the contact), what it was for, reminder rhythm (prefilled from Settings).
3. **Friend detail: a card log**, not a chat:
   - Top: a **Next reminder** card: date, tone level, why ("because 'after payday ya'"), the draft in a plain text box (editable, **Regenerate**), and **Open in WhatsApp**. Pressing it records "Reminder sent" (with **Undo**). On a non-due day the card shows the next date and a **Remind now** button instead, which drafts the message on demand.
   - Below: a stack of log cards, newest first, e.g. `💸 Lent Rp150k · Oct 12` · `📤 Reminder sent (gentle) · Oct 20` · `💬 Reply: "after payday ya" → Promise · Oct 25` · `💵 Paid Rp50k · Oct 26`.
   - Actions: **Log reply**, **Partial payment**, **Paid**.
   - No message bubbles and no "ask the AI" box: the app never talks to anyone.
4. **Log reply**: one text box → shows how it was read ("Promise · after payday → Oct 25") with **Looks right** / **Fix date** (date picker).
5. **Settings**: enable notifications (with an iPhone "Add to Home Screen" guide), default reminder rhythm, tone, default payday day, timezone (WIB / WITA / WIT).

### 4.1 Visual direction (not an "AI app" look)

- **Brand (@derbyps.dev):** dark mode by default. Purple `#9D4EDD`, Yellow `#FFC300`, Orange `#FF6B35`, Teal `#0F4C5C`. Teal is too dark for text: use it for surfaces and borders.
- **Roles:** Purple = primary actions (Open in WhatsApp, +); Yellow = "Remind today" dot and money amounts; Orange = "Promised today", firm tone, overdue; Teal = cards and dividers. Off-white text on a near-black background.
- **Motif: the kasbon book** — the warung debt notebook every Indonesian knows. Log cards look like torn receipt slips with monospace amounts; status changes appear as ink **rubber stamps** (`PROMISED`, `LUNAS` in orange when paid). Empty states and the header use a small hand-drawn ink line-art sloth, accents highlighting one detail only.
- **Avoid:** purple-to-blue gradients, glassmorphism, sparkle "✨ AI" icons, chat bubbles, generic rounded SaaS cards. The model is never shown as a character; it only fills in text.
- Fonts from Google Fonts: a characterful display face for headings and a monospace for amounts and dates (chosen during implementation).

## 5. Data model (SQLite)

- `users(id, username, password_hash, is_demo, tone, payday_day, timezone, default_rhythm, default_rhythm_day, created_at)`
- `debts(id, user_id, friend_name, phone, currency, amount, remaining, item, lent_on, due_on, rhythm, rhythm_day, level, firm_count, next_nudge_on, promise_on, status, created_at)`; `rhythm`: `weekly | biweekly | monthly`; `status`: `open | talk | paid`
- `events(id, debt_id, kind, text, parsed_json, created_at)`; `kind`: `lent | nudge | excuse | partial | paid`
- `push_subscriptions(id, user_id, endpoint, p256dh, auth)`
- `push_log(user_id, date)`

## 6. Demo for judges

- **Try the demo** creates a sandbox user with 4 fictional friends in different states (due today, tomorrow, waiting after a payday excuse, talk in person). Sandboxes older than 24 h are deleted.
- In demo mode, **Open in WhatsApp** opens `wa.me/?text=…` with no number; the visitor picks a contact.
- **Test notification** button sends a push to the visitor's own device.
- Caps: model calls per demo user per hour and per day overall (env vars), like BoldPrint.
- The post includes a GIF/video of the full flow on a phone.

## 7. Training and evaluation

**Data (`data/gen_dataset.py`)**: synthetic excuses generated *from* their gold label: pick `kind` + `when` and today's date, then render from code-mixed phrase banks (Jaksel English, Bahasa, slang, typos, emoji, filler such as "literally", "which is", "deh", "ya"). ~2,000 train rows. Some phrase families are held out for a synthetic test split. Labels are never guessed by an LLM.

**Real test set (`data/handwritten_test.jsonl`)**: ~60 excuses written by the author and the friend (fictional names, no real chats), each with today's date and gold kind + resolved date. Never used for training.

**Systems compared**: regex rules · base Qwen3-8B (prompted) · SFT · SFT+RL.

**Metrics**: resolved-date exact match; **too-early rate** (resolved date earlier than gold); kind accuracy; valid-JSON rate.

**RL reward**: exact date +1; too late −1; too early −5; wrong kind −2; invalid JSON −5.

**Budget caps** (`train/budget.py` guard, as in BoldPrint): SFT ≤ $1.00, RL ≤ $1.20, eval ≤ $0.30. Total ≤ $3; RL is skipped if SFT already meets the target or credit runs low.

## 8. Components

```
owemygod/
  owemygod/
    schema.py        # excuse-reader output model
    prompt.py        # shared prompts (train, eval, app), stop tokens
    resolve.py       # date expression → calendar date (Asia/Jakarta)
    schedule.py      # escalation ladder, next-nudge logic
    rules.py         # regex baseline (also the fallback reader)
    writer.py        # nudge prompt, guards, templates, placeholder fill
    model_client.py  # Tinker OpenAI-compatible client
    db.py            # SQLite schema and queries
    push.py          # web push send, VAPID
    money.py         # Rp150k formatting / parsing
  app/
    main.py          # FastAPI routes, auth, demo sandboxes, daily job
    templates/       # list, detail, add, settings, login
    static/          # css, app.js, sw.js, manifest.webmanifest, icons
  data/              # gen_dataset.py, phrase banks, handwritten_test.jsonl
  train/             # budget.py, check_setup.py, sft.py, rl.py, check_oai.py
  eval/              # run_eval.py, report.py → table.md, chart.png
  tests/
  render.yaml, README.md, RUNBOOK.md
```

## 9. Error handling

- Model down or invalid JSON → regex reader; the excuse screen says "Read by rules (model unavailable)" and the user can fix the date.
- Writer guard failure → template.
- Push subscription expired (404/410) → delete it.
- Every date shown to the user can be corrected by hand; the schedule always uses the corrected date.

## 10. Testing

pytest for `resolve`, `schedule`, `rules`, `writer` guards, `money`, `db`, and API routes (FastAPI TestClient, with a fake model client). The Tinker-dependent scripts get a dry-run mode that estimates cost without calling the API.

## 11. Privacy and risks

- Phone numbers and debts live only in SQLite on the Render disk. The model sees excuse text only, never names, numbers or amounts. The post states plainly that excuse text goes to Tinker's endpoint and that the weights are ours to move.
- Public demo and post use fictional people only.
- Tinker's OpenAI-compatible inference is beta and meant for low traffic; acceptable for one user plus judges, capped.
- Time: ~26 h. Order: data + SFT first (runs while the app is built) → app → push → deploy → eval → post (≥ 4 h for writing).
- Render prices (Starter $7, disk) not re-checked; verify in the dashboard before deploying.

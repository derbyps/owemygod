---
title: "OweMyGod: I trained an 8B model that reminding a friend one day too early is five times worse than one day too late"
published: false
tags: devchallenge, hf26challenge, ai, opensource
---

<!-- DRAFT. Fill every [[...]] from eval/out/table.md and your own experience before publishing.
     Title option with a number once the eval is in:
     "OweMyGod: my fine-tuned 8B model cut too-early debt reminders from [[base %]] to [[RL %]]" -->

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

## What I Built

In Indonesia there's a saying: *yang ngutang lebih galak*. The person who borrowed the money gets more offended
than the person who lent it.

[[One or two sentences about your friend, with their permission: they lend money, hate chasing it, and what
happened the last time they asked. Keep their name out or use a fictional one.]]

So I built **OweMyGod**, a sloth-paced debt reminder for friends who'll pay you back… eventually.

- The home screen looks like a chat list: who owes you, how much, and who is **due today** (bold, like an unread
  chat).
- When a friend replies, you log what they said. *"Abis gajian ya"* (after payday) and the app waits until the 25th.
  *"Besok gabisa, jumat aja"* (can't tomorrow, Friday then) and it waits for Friday.
- On the day, it drafts a reminder in the right tone (gentle, then playful, then firm) that refers back to their own
  excuse: *"udah gajian kan? 😄"*. You tap **Open in WhatsApp** and press send.
- One push notification at 09:00, only when someone is due or promised to pay today.
- It never sends two reminders within 3 days, and after three firm ones with no answer it tells you to talk in
  person and stops. Slow and steady keeps the friendship.

**The lazy payoff:** [[e.g. "My friend tracked N debts for a week: zero 'wait, who owed me?' moments, and the
reminders took one tap each instead of 10 minutes of agonising over the wording."]]

## Demo

[[Render URL]] → **Try the demo** gives you a private sandbox with four fictional friends in every state. Turn on
notifications in Settings and press **Send a test notification** to feel the 09:00 nudge.

[[GIF: home list → Budi "Promised today" → log reply "besok gabisa, jumat aja" → read as Friday → Sari's reminder
→ Open in WhatsApp]]

## Code

{% github [[your-github]]/owemygod %}

## How I Built It

### The model translates, code counts

The tempting design is "LLM, here's the excuse, what date should I remind them?" Language models are bad at
calendars. So the model never outputs a date. It outputs a *kind* of time:

```json
{"kind": "promise", "when": {"type": "payday"}}
```

There are seven kinds: tomorrow-ish, a weekday, next week, a day of the month, payday, start or end of the month.
Plain Python turns that into a date in your time zone (payday = the 25th, or whatever you set), and a small
schedule engine decides the next reminder. The model reads Jakarta slang; code does arithmetic.

### Fine-tuning on Tinker, with a reward that respects friendship

The reader is Qwen3-8B with a LoRA adapter trained on [Tinker](https://thinkingmachines.ai/tinker/):

1. **SFT on 2,000 synthetic replies** in English–Indonesian code-mix ("literally", "which is", "deh", "bsk",
   typos, emoji). Each reply is generated *from* its label, so the labels are never guessed by another model.
   Hard cases are included on purpose: *"besok gabisa, jumat aja"* (the later time wins), *"tanggal muda"* (early
   in the month), *"gajian tgl 1"* (the explicit date beats "payday"), *"abis THR"* (no fixed date, so vague).
2. **RL with a lopsided reward.** Reminding someone before the day they promised is rude; reminding them a day late
   just costs a day. So: exact date +1, too late −1, **too early −5**, wrong kind −2, broken JSON −5.

Total Tinker spend: [[≈ $X]].

### Results

[[Paste eval/out/table.md here. Comment honestly on it, e.g.: keyword rules do fine on easy phrasings; where the
model earns its keep is contradictions and slang. Name 2–3 real examples from the hand-written set where rules
failed and the model didn't, and at least one where the model still fails.]]

![Too-early reminders by system]([[chart.png URL]])

### The app

FastAPI, server-rendered HTML and a tiny bit of JavaScript, SQLite on a Render disk, and Web Push (one standard for
Android Chrome and iPhone home-screen apps on iOS 16.4+). The design is a *buku kasbon*, the debt notebook every
Indonesian corner shop keeps: the history is a stack of paper slips, replies are in handwriting, and paid debts get
a **LUNAS** stamp.

If the model is down, keyword rules read replies and templates write reminders, and the screen says so.

## Why Open Matters

- **I own the weights.** The adapter is mine. If Tinker's endpoint changes, or I want it on my own laptop, I can
  move it. For an app that holds friends' money troubles, I don't want to depend on someone else's model staying
  the same.
- **A small, specialised model is enough.** Reading "abis gajian ya" doesn't need a frontier model. An 8B model
  trained for this one job is cheap to run: [[cost per 1,000 replies]].
- **Privacy by design, honestly stated.** Names, phone numbers and amounts never go to any model; they stay in the
  app's database. The writer works with `{name}` and `{amount}` placeholders. The text of a logged reply *is* sent to
  Tinker's inference endpoint to be read; that's the trade-off, and with open weights I can remove it later by
  hosting the model myself.
- **The reward is mine to choose.** "Too early is five times worse than too late" is a value judgement about
  friendship. With an open model and Tinker's training loop I could put that judgement into the model itself.

## Prize Categories

- **Best Use of Tinker:** SFT + RL with a custom asymmetric reward on Qwen3-8B; serving through Tinker's
  OpenAI-compatible endpoint; base vs. SFT vs. RL measured on held-out and hand-written replies.
- **Best Use of Render:** a Blueprint (`render.yaml`) with a Starter web service, a persistent disk for SQLite, an
  in-process daily scheduler that sends the 09:00 pushes, secrets kept out of the repo, and a `/healthz` that reports
  whether the model is reachable.

<!-- Optional: embed the DevRelay agent session. -->

Team: solo. Built with help from Claude Code.

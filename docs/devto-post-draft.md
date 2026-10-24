---
title: "OweMyGod: a fine-tuned 8B model reads Jakarta debt excuses right 92% of the time (keyword rules: 60%)"
published: false
tags: devchallenge, hf26challenge, ai, opensource
---

<!-- DRAFT. Fill every remaining [[...]] from your own experience before publishing.
     Alt title: "OweMyGod: I tried to teach an 8B model that nagging a friend one day early is 5× worse than one day late" -->

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

### Fine-tuning on Tinker, and what RL taught me

The reader is Qwen3-8B with a LoRA adapter trained on [Tinker](https://thinkingmachines.ai/tinker/), on 2,000
synthetic replies in English–Indonesian code-mix ("literally", "which is", "deh", "bsk", typos, emoji). Each reply is
generated *from* its label, so labels are never guessed by another model.

**Round 1 humbled me.** My keyword-rules baseline scored 91% on my own synthetic test, because I wrote both. So I
asked a friend to write 50 replies the way they'd really text. On those, rules got 50% and my first fine-tune 80%,
but it still reminded **too early 14% of the time**. Almost every miss was the same: *"tgl 28 ya pas payday"*
→ the model said "payday" (the 25th) instead of the date the friend actually named.

**Round 2** fixed the generator for what that *dev set* exposed (an explicit date beats payday, *pertengahan bulan*
is the 15th, *tar malam* is today) and retrained. Then we wrote **25 brand-new replies** and ran them once.

**RL found nothing to fix, and I'm keeping that in the story.** I'd planned reinforcement learning with a lopsided
reward (exact +1, late −1, **too early −5**), because a too-early reminder is the one that costs a friendship. It
ran twice, and both times the fine-tuned model answered every training reply identically and correctly, so there
was no difference to learn from (`trained_on=0`). The honest lesson: once the data covered the hard patterns,
supervised fine-tuning was enough. Total Tinker spend: about $2.40 [[check the Tinker console]].

### Results (25 hand-written replies, never seen in training, evaluated once)

| System | Exact date ↑ | Too early ↓ | Kind right ↑ |
|---|---|---|---|
| Keyword rules | 60% | 16% | 84% |
| Qwen3-8B, untrained | 68% | 12% | 80% |
| Fine-tuned v1 | 80% | 12% | 92% |
| **Fine-tuned v2 (shipped)** | **92%** | **8%** | **100%** |

Both remaining misses are one day early, and both are genuinely tricky: *"tgl 25 pas payday ya! eh tgl 25 minggu
kan ya? senin deh"* (it kept the 25th, not the corrected Monday) and *"akhir bulan ya bro tgl 28/29"* (it picked the
28th). That's why the app always shows how it read a reply and lets you fix the date in one tap.

![Too-early reminders by system]([[upload eval/out/chart.png]])

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
  trained for this one job beats keyword rules by 32 points on real replies, and costs a fraction of a cent per reply.
- **Privacy by design, honestly stated.** Names, phone numbers and amounts never go to any model; they stay in the
  app's database. The writer works with `{name}` and `{amount}` placeholders. The text of a logged reply *is* sent to
  Tinker's inference endpoint to be read; that's the trade-off, and with open weights I can remove it later by
  hosting the model myself.
- **I could measure and fix it myself.** With open weights and Tinker's training loop I found a specific failure
  ("payday" beating the date they named), fixed the data and retrained in an afternoon, for about a dollar.

## Prize Categories

- **Best Use of Tinker:** LoRA SFT of Qwen3-8B in two rounds driven by a hand-written dev set, an RL loop with a
  custom asymmetric reward (and an honest account of why it had nothing to learn), and the shipped adapter served
  through Tinker's OpenAI-compatible endpoint; rules vs. base vs. v1 vs. v2 on a clean hand-written test.
- **Best Use of Render:** a Blueprint (`render.yaml`) with a Starter web service, a persistent disk for SQLite, an
  in-process daily scheduler that sends the 09:00 pushes, secrets kept out of the repo, and a `/healthz` that reports
  whether the model is reachable.

<!-- Optional: embed the DevRelay agent session. -->

Team: solo. Built with help from Claude Code.

# Hand-written test set (you + your friend)

The real test of the model. About **60 replies**, written by people, never used for training.
Use **made-up names**; never paste real chats or phone numbers.

One JSON object per line in `handwritten_test.jsonl`:

```json
{"id": "hw-01", "today": "2026-10-23", "reply": "sorry bgt, abis gajian ya literally langsung", "target": {"kind": "promise", "when": {"type": "payday"}}}
{"id": "hw-02", "today": "2026-10-23", "reply": "nanti ya lagi tight", "target": {"kind": "vague"}}
{"id": "hw-03", "today": "2026-10-23", "reply": "udah aku tf kemarin cek deh", "target": {"kind": "claims_paid"}}
```

- `today`: the day the reply was "received". Vary it (different weekdays, near month ends).
- `kind`: `promise` (gives a time), `vague` (no time), `claims_paid` (says they already paid).
- `when` (promises only), one of:
  `{"type":"relative_days","n":1}` · `{"type":"weekday","day":"fri"}` · `{"type":"next_week"}` ·
  `{"type":"day_of_month","day":25}` · `{"type":"payday"}` · `{"type":"month_start"}` · `{"type":"month_end"}`
- If two times are mentioned, label the one they finally commit to.

Aim for roughly 40 promises, 12 vague, 8 claims-paid. Write the way your friends really text:
typos, slang, emoji, English–Indonesian mix. Tricky ones are the most valuable
("besok gabisa, jumat aja ya", "tgl 30an", "abis THR" → vague, since THR has no fixed date here).

Check your file: `python -c "import json; [json.loads(l) for l in open('data/handwritten_test.jsonl')]"`.

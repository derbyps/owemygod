"""Phrase banks for synthetic replies: Jaksel English, Bahasa and slang.

Each family is a way of saying one kind of time. `{t}` is replaced by a time phrase for that
family's expression type. One family per type is held out of training (`heldout=True`) so the
synthetic test set checks phrasings the model never saw.
"""
from __future__ import annotations

WEEKDAY_ID = {"mon": "senin", "tue": "selasa", "wed": "rabu", "thu": "kamis", "fri": "jumat", "sat": "sabtu",
              "sun": "minggu"}
WEEKDAY_EN = {"mon": "monday", "tue": "tuesday", "wed": "wednesday", "thu": "thursday", "fri": "friday",
              "sat": "saturday", "sun": "sunday"}

# Time phrases per expression type. Keys: n for relative_days, weekday code, or day of month.
REL_ID = {0: ["hari ini", "ntar sore", "malem ini"], 1: ["besok", "besok pagi", "besok siang"],
          2: ["lusa", "2 hari lagi"], 3: ["3 hari lagi"], 4: ["4 hari lagi"], 5: ["5 hari lagi"]}
REL_EN = {0: ["today", "tonight", "later today"], 1: ["tomorrow", "tmrw", "tomorrow morning"],
          2: ["the day after tomorrow", "in 2 days"], 3: ["in 3 days"], 4: ["in 4 days"], 5: ["in 5 days"]}
REL_SHORT = {0: ["hr ini", "ntr mlm"], 1: ["bsk", "besok2"], 2: ["lusa dh"], 3: ["3hr lg"], 4: ["4hr lg"],
             5: ["5hr lg"]}

FAMILIES: dict[str, dict] = {
    # relative_days
    "rel_id": {"type": "relative_days", "times": REL_ID, "templates": [
        "{t} aku transfer ya", "{t} ya pasti", "aku ganti {t} ya", "{t} deh aku tf"]},
    "rel_en": {"type": "relative_days", "times": REL_EN, "templates": [
        "I'll pay you {t}", "{t} ya promise", "sending it {t}", "{t} for sure"]},
    "rel_mixed": {"type": "relative_days", "times": REL_EN, "templates": [
        "{t} literally langsung aku tf", "{t} ya, which is pasti", "sorry, {t} aku transfer"]},
    "rel_short": {"type": "relative_days", "times": REL_SHORT, "heldout": True, "templates": [
        "{t} ya", "{t} kutf", "otw {t}"]},
    # weekday
    "wd_id": {"type": "weekday", "times": {k: [v, f"hari {v}"] for k, v in WEEKDAY_ID.items() if k != "sun"},
              "templates": ["{t} aku transfer ya", "{t} ini ya", "paling {t} deh"]},
    "wd_en": {"type": "weekday", "times": {**{k: [v, f"this {v}"] for k, v in WEEKDAY_EN.items()},
                                           "sat": ["saturday", "this weekend", "weekend ini"]},
              "templates": ["I'll send it {t}", "{t} ya promise", "by {t} for sure"]},
    "wd_mixed": {"type": "weekday", "times": {k: [v] for k, v in WEEKDAY_EN.items()}, "heldout": True,
                 "templates": ["{t} ini literally aku tf", "basically {t} ya", "{t} deh, janji"]},
    # next_week
    "nw_id": {"type": "next_week", "times": {None: ["minggu depan", "pekan depan", "minggu dpn"]},
              "templates": ["{t} ya", "{t} aku ganti", "{t} pasti"]},
    "nw_en": {"type": "next_week", "times": {None: ["next week", "sometime next week"]},
              "templates": ["{t} ya promise", "I'll pay you {t}", "{t} for sure bro"]},
    "nw_mixed": {"type": "next_week", "times": {None: ["next week", "minggu depan"]}, "heldout": True,
                 "templates": ["{t} literally ya", "which is {t} aku tf", "{t} deh, lagi tight"]},
    # day_of_month
    "dom_id": {"type": "day_of_month", "times": "dom_id", "templates": [
        "{t} aku transfer", "{t} ya", "paling lambat {t}"]},
    "dom_en": {"type": "day_of_month", "times": "dom_en", "templates": [
        "I'll pay on the {t}", "by the {t} ya", "{t} promise"]},
    "dom_short": {"type": "day_of_month", "times": "dom_short", "heldout": True, "templates": [
        "{t} ya", "{t} kutf", "tunggu {t} ya"]},
    # payday
    "pay_id": {"type": "payday", "times": {None: ["abis gajian", "pas gajian", "nunggu gajian", "gaji turun"]},
               "templates": ["{t} ya", "{t} aku langsung tf", "tunggu {t} dulu ya"]},
    "pay_en": {"type": "payday", "times": {None: ["after payday", "on payday", "when I get paid"]},
               "templates": ["{t} ya promise", "I'll send it {t}", "{t} for sure"]},
    "pay_mixed": {"type": "payday", "times": {None: ["after payday", "abis gajian"]}, "heldout": True,
                  "templates": ["literally {t} langsung", "{t} deh, lagi bokek", "which is {t} ya"]},
    # month_start
    "ms_id": {"type": "month_start", "times": {None: ["awal bulan", "awal bulan depan", "begitu ganti bulan",
                                                      "tanggal muda", "pas tgl muda"]},
              "templates": ["{t} ya", "{t} aku ganti", "tunggu {t} ya"]},
    "ms_en": {"type": "month_start", "times": {None: ["early next month", "first thing next month"]},
              "templates": ["{t} ya promise", "I'll pay {t}", "{t} for sure"]},
    "ms_mixed": {"type": "month_start", "times": {None: ["tgl muda", "early next month", "awal bulan"]},
                 "heldout": True,
                 "templates": ["{t} literally ya", "basically {t} deh", "{t} ya, sorry lama"]},
    # month_end
    "me_id": {"type": "month_end", "times": {None: ["akhir bulan", "akhir bulan ini", "ujung bulan"]},
              "templates": ["{t} ya", "{t} aku transfer", "paling {t}"]},
    "me_en": {"type": "month_end", "times": {None: ["end of the month", "end of month", "before the month ends"]},
              "templates": ["{t} ya promise", "I'll pay you {t}", "by {t}"]},
    "me_mixed": {"type": "month_end", "times": {None: ["end of month", "akhir bulan"]}, "heldout": True,
                 "templates": ["{t} literally aku tf", "which is {t} ya", "{t} deh janji"]},
    # vague
    "vague_id": {"kind": "vague", "templates": [
        "nanti ya", "kapan2 deh", "pasti diganti kok", "aku usahain ya", "sabar ya", "nanti aku kabarin"]},
    "vague_en": {"kind": "vague", "templates": [
        "soon ya", "I'll pay you back, promise", "working on it", "sorry, I haven't forgotten"]},
    "vague_mixed": {"kind": "vague", "heldout": True, "templates": [
        "lagi tight banget sorry", "literally lagi bokek, nanti ya", "which is pasti kok, sabar",
        "nunggu bonus cair ya", "abis THR deh", "kalau udah ada rezeki ya", "besok? belum tau sih"]},
    "vague_time_words": {"kind": "vague", "templates": [
        "minggu ini lagi kacau, nanti aku kabarin", "nunggu THR ya", "kalau project cair aku tf",
        "gajian kemarin udah abis literally, nanti ya", "next week? hmm not sure yet"]},
    # claims_paid
    "paid_id": {"kind": "claims_paid", "templates": [
        "udah aku transfer kok", "cek deh udah masuk", "udah tf semalem", "barusan aku tf"]},
    "paid_en": {"kind": "claims_paid", "templates": [
        "already sent it", "I paid you yesterday", "check your account, sent"]},
    "paid_mixed": {"kind": "claims_paid", "heldout": True, "templates": [
        "udah aku send literally kemarin", "basically udah lunas ya", "udah ku tf, cek mutasi"]},
}

# Excuses that come before or after the time, to make replies realistic.
OPENERS = ["sorry bgt ya", "aduh lupa", "omg sorry", "hehe iya", "iya iya", "maaf ya", "eh iya",
           "sorry bro", "lagi tight banget", "abis beli susu", "kemarin abis bayar kos", "duh"]
FILLERS = ["ya", "deh", "sih", "ok", "bro", "beb", "literally", "basically", "promise"]
EMOJI = ["🙏", "😭", "🥲", "😅", "🙇", "💸", ""]

# Replies that mention an earlier time first, then commit to a later one (the later one is the answer).
COMPOUND = ["{early} gak bisa, {t} aja ya", "{early}? duh gabisa, {t} deh", "not {early} sorry, {t} ya",
            "tadinya {early}, tapi {t} aja ya", "{early} kayaknya gak sempet, {t} pasti"]
EARLY_BY_TYPE = {
    "relative_days": ["hari ini", "today"],
    "weekday": ["besok", "tomorrow", "hari ini"],
    "next_week": ["besok", "tomorrow", "minggu ini", "this week"],
    "day_of_month": ["besok", "tomorrow", "minggu ini"],
    "payday": ["besok", "tomorrow", "minggu ini"],
    "month_start": ["besok", "minggu ini", "this week", "akhir bulan"],
    "month_end": ["besok", "tomorrow", "minggu ini"],
}
# Payday phrased with an explicit date: the date wins over "payday".
PAYDAY_WITH_DATE = ["gajian tgl {d}, langsung aku tf", "gaji turun tgl {d} ya", "payday is the {d}th, I'll send it then"]

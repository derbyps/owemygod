import pytest

from owemygod.rules import read_by_rules


@pytest.mark.parametrize("text,kind,typ", [
    ("besok ya", "promise", "relative_days"),
    ("tomorrow for sure", "promise", "relative_days"),
    ("lusa deh", "promise", "relative_days"),
    ("minggu depan deh", "promise", "next_week"),
    ("next week ya", "promise", "next_week"),
    ("jumat aku transfer", "promise", "weekday"),
    ("this friday promise", "promise", "weekday"),
    ("tanggal 25 aku transfer", "promise", "day_of_month"),
    ("abis gajian ya bro", "promise", "payday"),
    ("after payday", "promise", "payday"),
    ("awal bulan ya", "promise", "month_start"),
    ("akhir bulan deh", "promise", "month_end"),
    ("udah aku transfer kok", "claims_paid", None),
    ("nanti ya", "vague", None),
    ("", "vague", None),
])
def test_rules(text, kind, typ):
    r = read_by_rules(text)
    assert r.kind == kind and (r.when.type if r.when else None) == typ


def test_rules_values():
    assert read_by_rules("lusa").when.n == 2
    assert read_by_rules("tgl 30 ya").when.day == 30
    assert read_by_rules("hari jumat").when.day == "fri"

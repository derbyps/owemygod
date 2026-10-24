import pytest

from owemygod.money import format_amount, parse_amount, totals


@pytest.mark.parametrize("s,n", [("150k", 150_000), ("150rb", 150_000), ("150 ribu", 150_000), ("Rp 150.000", 150_000),
                                 ("1.2jt", 1_200_000), ("1,5jt", 1_500_000), ("2 juta", 2_000_000), ("75000", 75_000),
                                 ("Rp75,000", 75_000)])
def test_parse(s, n): assert parse_amount(s) == n


@pytest.mark.parametrize("bad", ["", "abc", "-5k", "0", "1.2.3jt"])
def test_parse_bad(bad):
    with pytest.raises(ValueError):
        parse_amount(bad)


@pytest.mark.parametrize("n,s", [(150_000, "Rp150k"), (1_200_000, "Rp1.2jt"), (1_250_000, "Rp1.25jt"),
                                 (7_500, "Rp7.5k"), (500, "Rp500"), (2_000_000, "Rp2jt")])
def test_format(n, s): assert format_amount(n) == s


@pytest.mark.parametrize("s,n", [("40", 4000), ("$12.50", 1250), ("12,5", 1250), ("$ 7", 700)])
def test_parse_usd(s, n): assert parse_amount(s, "USD") == n


@pytest.mark.parametrize("n,s", [(4000, "$40"), (1250, "$12.50"), (5, "$0.05")])
def test_format_usd(n, s): assert format_amount(n, "USD") == s


def test_totals():
    assert totals([{"currency": "IDR", "remaining": 1_250_000, "status": "open"},
                   {"currency": "USD", "remaining": 4000, "status": "open"},
                   {"currency": "IDR", "remaining": 99_000, "status": "paid"}]) == "Rp1.25jt · $40"


def test_totals_empty(): assert totals([]) == "Rp0"

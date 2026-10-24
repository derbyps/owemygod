import pytest

from owemygod.phone import normalize, wa_link


@pytest.mark.parametrize("raw", ["0812-3456-789", "+62 812 3456 789", "628123456789", "(0812) 3456 789"])
def test_phone(raw): assert normalize(raw) == "628123456789"


@pytest.mark.parametrize("raw", ["", "  ", "abc", "12"])
def test_phone_empty_or_bad(raw): assert normalize(raw) is None


def test_wa_link_no_number(): assert wa_link(None, "hi ya") == "https://wa.me/?text=hi%20ya"
def test_wa_link_number(): assert wa_link("628123456789", "Rp150k 🙏").startswith("https://wa.me/628123456789?text=Rp150k%20")

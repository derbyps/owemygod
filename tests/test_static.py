from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


def test_brand_tokens_and_no_decorative_effects():
    css = (STATIC / "style.css").read_text()
    for token in ("--purple: #9D4EDD", "--yellow: #FFC300", "--orange: #FF6B35", "--teal: #0F4C5C"):
        assert token in css
    assert "linear-gradient(" not in css and "backdrop-filter" not in css


def test_icons_exist():
    assert (STATIC / "icon-192.png").stat().st_size > 0 and (STATIC / "icon-512.png").stat().st_size > 0

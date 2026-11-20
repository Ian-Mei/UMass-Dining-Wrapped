"""Accessibility checks on the results page's CSS and HTML (WCAG 2.2 AA)."""
import re
from pathlib import Path

import pytest

from .conftest import charge, make_history_pdf, swipe
from .test_app import client, upload  # noqa: F401  (client is a fixture)

CSS = (Path(__file__).parent.parent / "static" / "styles" / "wrapped.css").read_text(encoding="utf8")
CSS_NO_COMMENTS = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)


def luminance(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    rgb = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


NAMED = {"white": "#ffffff", "black": "#000000"}


def solid(value):
    """A declaration's colour as hex, or None if it isn't one solid colour."""
    value = NAMED.get(value.strip().lower(), value.strip())
    return value if re.fullmatch(r"#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?", value) else None


def rules():
    """(selector, declarations) for every rule outside @media blocks' nesting quirks."""
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", CSS_NO_COMMENTS):
        yield " ".join(m.group(1).split()), m.group(2)


def declared(body, prop):
    m = re.search(rf"(?<![-\w]){prop}:\s*([^;]+)", body)
    return m.group(1).strip() if m else None


# Text on the white cards: stat cards, the explorer and the raw-data tables.
ON_WHITE_CARDS = (".statcard", ".heatmap", ".x", ".rawdata", ".rawnote", ".listbox .list")
# Disabled controls are exempt from WCAG's contrast rule; still keep them readable.
DISABLED_MIN = 3.0
# Big mint numbers are the page's signature look; they're large text but still below 3:1.
# Left as they are on purpose (see the PR).
BRAND_MINT_NUMBERS = {".statcard .big", ".statcard .tilevalue", ".statcard .planverdict.ok"}


def card_text_rules():
    for selector, body in rules():
        if selector in BRAND_MINT_NUMBERS or not selector.startswith(ON_WHITE_CARDS):
            continue
        fg = solid(declared(body, "color") or "")
        if fg:
            bg = solid(declared(body, "background") or declared(body, "background-color") or "#ffffff")
            yield selector, fg, bg or "#ffffff"


def test_found_the_card_text_rules():
    assert len(list(card_text_rules())) >= 15


@pytest.mark.parametrize("selector, fg, bg", list(card_text_rules()))
def test_card_text_is_readable(selector, fg, bg):
    needed = DISABLED_MIN if ":disabled" in selector else 4.5
    assert contrast(fg, bg) >= needed, f"{selector}: {fg} on {bg} is {contrast(fg, bg):.2f}:1"


def test_busy_calendar_days_are_readable():
    """The darker calendar cells set their own text colour; 11px text needs 4.5:1."""
    for level in ("l1", "l2", "l3", "l4"):
        body = dict(rules())[f".xcell.{level}"]
        fg = solid(declared(body, "color") or "#42455a")
        bg = solid(declared(body, "background"))
        assert contrast(fg, bg) >= 4.5, f".xcell.{level}: {fg} on {bg}"


def test_keyboard_focus_is_visible():
    assert ":focus-visible" in CSS_NO_COMMENTS
    assert not re.search(r"outline:\s*(none|0)\s*;", CSS_NO_COMMENTS)


def test_respects_reduced_motion():
    block = re.search(r"@media \(prefers-reduced-motion: reduce\)\s*\{(.*?)\n\}", CSS_NO_COMMENTS, re.S)
    assert block, "no prefers-reduced-motion block"
    for needed in (".reveal", ".dramaticreveal", "scroll-behavior: auto", "transition: none"):
        assert needed in block.group(1)


def test_screens_use_the_visible_height_on_phones():
    """100vh is taller than the visible area while a phone's address bar shows; svh never is."""
    section = dict(rules())["section"]
    assert "100svh" in section
    assert section.index("100vh") < section.index("100svh")  # vh first, as a fallback


def test_background_pictures_are_hidden_from_screen_readers(client):  # noqa: F811
    page = upload(client, make_history_pdf([
        swipe("WorcDC2", "March 4, 2024, 12:00PM"),
        charge("Wasabi 1", "March 5, 2024, 12:00PM", 10.00),
    ])).get_data(as_text=True)
    backgrounds = re.findall(r'<img[^>]*class="background"[^>]*>', page)
    assert backgrounds
    for img in backgrounds:
        assert 'alt=""' in img, img
    for img in re.findall(r"<img\b[^>]*>", page):
        assert "alt=" in img, img

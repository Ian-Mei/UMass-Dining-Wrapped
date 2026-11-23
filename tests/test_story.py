"""The Wrapped-style results page: one full-screen story with the owner's art."""
import re
from pathlib import Path

from tools.cut_sprites import anchor_style

from .conftest import charge, make_history_pdf, swipe
from .test_accessibility import contrast
from .test_app import client, upload  # noqa: F401  (client is a fixture)

ROOT = Path(__file__).parent.parent


def story_css():
    return (ROOT / "static" / "styles" / "story.css").read_text(encoding="utf8")


def page(client):  # noqa: F811
    return upload(client, make_history_pdf([
        swipe("WorcDC2", "March 4, 2024, 12:00PM"),
        swipe("WorcDC2", "March 5, 2024, 12:00PM"),
        charge("Wasabi 1", "March 5, 2024, 1:00PM", 10.00),
    ])).get_data(as_text=True)


def test_art_stays_on_the_edges_it_was_cut_by():
    assert anchor_style(0, 0, 422, 403) == "--w:422;left:0;top:0"
    assert anchor_style(1313, 0, 607, 474) == "--w:607;right:0;top:0"
    assert anchor_style(0, 596, 583, 484) == "--w:583;left:0;bottom:0"
    assert anchor_style(960, 540, 100, 100) == "--w:100;left:50.00%;top:50.00%"


def test_no_screen_stretches_a_background_picture(client):  # noqa: F811
    assert 'class="background"' not in page(client)


def test_every_screen_has_art_on_a_solid_color(client):  # noqa: F811
    html = page(client)
    for screen in re.findall(r"<section\b.*?</section>", html, re.S):
        assert 'class="art' in screen, screen[:60]
    for sprite in re.findall(r'<img class="sprite[^>]*>', html):
        for needed in ('alt=""', 'loading="lazy"', "width=", "height="):
            assert needed in sprite


def test_every_color_keeps_its_text_readable():
    pairs = re.findall(r"--scene:\s*(#[0-9a-f]{3,6});\s*--fg:\s*(#[0-9a-f]{3,6});", story_css())
    assert len(pairs) == 6
    for scene, fg in pairs:
        assert contrast(fg, scene) >= 4.5, (fg, scene)


def test_the_story_builds_to_the_share_card(client):  # noqa: F811
    html = page(client)
    order = [html.index(s) for s in ('id="favIntro"', 'id="favDC"', 'id="personality"', 'id = "card"', 'id="days"', '<section id="end">')]
    assert order == sorted(order)


def test_share_card_has_a_real_share_button(client):  # noqa: F811
    card = page(client).split('id = "card"')[1]
    assert 'class="poster"' in card
    assert 'data-semester="' in card
    assert 'class="sharebtn"' in card


def test_screens_only_wait_for_animation_when_javascript_runs(client):  # noqa: F811
    html = page(client)
    assert 'document.documentElement.classList.add("js")' in html[:html.index("</head>")]
    assert ".js section:not(.in) .container" in story_css()


def test_motion_stops_for_reduced_motion():
    block = story_css().split("@media (prefers-reduced-motion: reduce)")[1]
    assert "animation: none" in block


def test_font_cant_block_the_page(client):  # noqa: F811
    html = page(client)
    assert re.search(r'<link[^>]*family=Archivo[^>]*media="print"[^>]*onload="this\.media=\'all\'"', html)
    assert "@import" not in (ROOT / "static" / "styles" / "wrapped.css").read_text(encoding="utf8")


def test_busiest_day_note_names_its_new_color():
    script = (ROOT / "static" / "scripts" / "explorer.js").read_text(encoding="utf8")
    assert "Coral: your busiest day" in script
    assert "Gold:" not in script


def test_list_rows_keep_name_and_value_on_one_line():
    assert ".statcard .listitem .itemname" in story_css()
    assert "grid-column: auto" in story_css()

"""The Wrapped-style results page: one full-screen story with the owner's art."""
import re
from pathlib import Path

import pytest

from tools.cut_sprites import JOINED, grouped
from tools.screens import SCREENS, placement, text_color

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


def test_no_screen_stretches_a_background_picture(client):  # noqa: F811
    assert 'class="background"' not in page(client)


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
    assert 'classList.add("js")' not in html  # if story.js fails to load, nothing stays hidden
    script = (ROOT / "static" / "scripts" / "story.js").read_text(encoding="utf8")
    assert 'document.documentElement.classList.add("js")' in script
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


def test_stats_dont_link_ahead_past_the_animation(client):  # noqa: F811
    html = upload(client, make_history_pdf(
        [swipe("Wasabi 1", f"03/{day:02d}/24 12:00:00 PM") for day in range(4, 12)]
        + [swipe("Harvest Market 1", f"03/{day:02d}/24 06:00:00 PM") for day in range(4, 12)]
        + [charge("Tavola 1", "03/12/24 01:00:00 PM", 10.00)]
    )).get_data(as_text=True)
    before_card = html[:html.index('id = "card"')]
    assert "data-explore-place" not in before_card
    assert "Tap a spot" not in html
    assert "See every visit" not in html


def test_screens_show_the_blending_backdrop_only_when_it_runs():
    css = story_css()
    assert "background: var(--section-bg, var(--scene));" in css
    assert "html.blend" in css
    assert "--section-bg: transparent" in css
    assert ".story-backdrop" in css
    reduced = css.split("@media (prefers-reduced-motion: reduce)")[1]
    assert ".art" in reduced


def test_art_crossfades_in_place_so_its_cut_edges_never_show():
    rule = re.search(r"html\.blend section \.art \{([^}]*)\}", story_css()).group(1)
    assert "position: fixed" in rule
    assert "translate" not in rule
    assert "scale: calc(1 + var(--away, 0)" in rule  # only ever larger, so edges stay off-screen


def test_one_screens_art_is_gone_before_the_next_appears():
    css = story_css()
    art = re.search(r"html\.blend section \.art \{([^}]*)\}", css).group(1)
    content = re.search(r"html\.blend section\.in \.container, html\.blend section\.in \.shareline \{([^}]*)\}", css).group(1)
    for rule in (art, content):
        fade = float(re.search(r"opacity: calc\(1 - var\(--away, 0\) \* ([\d.]+)\)", rule).group(1))
        assert fade >= 2  # fully faded by the halfway point


def test_short_laptops_put_the_personality_card_beside_the_wheel():
    block = story_css().split("@media (min-width: 761px) and (max-height: 820px)")[1]
    assert "grid-template-columns" in block
    assert "#personality .wheelinfo" in block
    assert "overflow-y: auto" in block  # a very long blurb scrolls inside the card


def test_wheel_spins_in_the_middle_then_slides_to_its_place():
    css = story_css()
    assert "#wheel.wheel-js:not(.landed) .wheelstage" in css
    assert "translate(var(--wheel-x, 0), var(--wheel-y, 0))" in css
    assert re.search(r"#wheel\.wheel-js\.landed \.wheelstage \{[^}]*transition: transform", css)
    assert re.search(r"#wheel\.wheel-js\.landed \.wheelinfo \{[^}]*transition:", css)


def test_reduced_motion_lands_the_wheel_without_sliding():
    block = story_css().split("@media (prefers-reduced-motion: reduce)")[1]
    assert "#wheel.wheel-js.landed .wheelstage, #wheel.wheel-js:not(.landed) .wheelstage" in block
    assert "#wheel.wheel-js.landed .wheelinfo, #wheel.wheel-js:not(.landed) .wheelinfo" in block


def test_laundry_only_share_card_has_no_zero_day_streak(client):  # noqa: F811
    rows = [["Student Debit Plan", "10/07/26 01:41:00 PM", "X - OAK DRYER 10", "-$1.40", "$5.80"]]
    html = upload(client, make_history_pdf(rows)).get_data(as_text=True)
    poster = html[html.index('class="poster"'):html.index("posterstamp")]
    assert "day streak" not in poster
    assert "personalities" in poster


def test_art_is_placed_again_when_the_real_font_arrives():
    script = (ROOT / "static" / "scripts" / "story.js").read_text(encoding="utf8")
    assert '"loadingdone"' in script


def test_art_placement_ignores_the_entrance_animation():
    script = (ROOT / "static" / "scripts" / "story.js").read_text(encoding="utf8")
    assert "DOMMatrixReadOnly" in script


def test_share_image_keeps_the_condensed_type():
    script = (ROOT / "static" / "scripts" / "share-card.js").read_text(encoding="utf8")
    assert script.count("ctx.font =") == 1  # one helper, which sets the stretch right after
    assert 'ctx.fontStretch = "condensed"' in script


def test_laundry_intro_matches_the_other_screens(client):  # noqa: F811
    rows = [["Student Debit Plan", "10/07/26 01:41:00 PM", "X - OAK DRYER 10", "-$1.40", "$5.80"]]
    assert '<section id="laundry" class="stat">' in upload(client, make_history_pdf(rows)).get_data(as_text=True)


def test_blue_wall_bars_use_a_visible_periwinkle():
    bar = re.search(r"\.statcard \.barrow \.bar \{([^}]*)\}", story_css()).group(1)
    color = re.search(r"background:\s*(#[0-9a-f]{6})", bar).group(1)
    assert contrast(color, "#fff6e9") >= 3


def test_share_card_shows_unique_places_visited(client):  # noqa: F811
    html = upload(client, make_history_pdf([
        swipe("WorcDC2", "March 4, 2024, 12:00PM"),
        swipe("WorcDC2", "March 5, 2024, 12:00PM"),
        charge("Wasabi 1", "March 5, 2024, 1:00PM", 10.00),
    ])).get_data(as_text=True)
    poster = html[html.index('class="poster"'):html.index("posterstamp")]
    assert "<b>2</b><span>places visited</span>" in poster
    assert "day streak" not in poster


def test_share_card_says_place_for_just_one(client):  # noqa: F811
    html = upload(client, make_history_pdf([swipe("WorcDC2", "March 4, 2024, 12:00PM")])).get_data(as_text=True)
    assert "<b>1</b><span>place visited</span>" in html[html.index('class="poster"'):html.index("posterstamp")]


def test_pieces_of_one_drawing_are_grouped_in_order():
    assert grouped(5, [(1, 3)]) == [(0,), (1, 3), (2,), (4,)]
    assert grouped(3, []) == [(0,), (1,), (2,)]


CORNER = {"L": True, "R": False, "T": True, "B": False}
TOP_ONLY = {"L": False, "R": False, "T": True, "B": False}
LEFT_ONLY = {"L": True, "R": False, "T": False, "B": False}
WHOLE = {"L": False, "R": False, "T": False, "B": False}


def test_art_can_move_to_any_edge_that_hides_its_cut_side():
    assert placement(CORNER, ("TL",)) == ("left:0;top:0;--ox:0%;--oy:0%", 1, 1, "corner")
    assert placement(CORNER, ("BR",)) == ("right:0;bottom:0;--ox:100%;--oy:100%", -1, -1, "corner")
    assert placement(TOP_ONLY, ("B", 40)) == ("left:40%;bottom:0;--ox:50%;--oy:100%", 1, -1, "mid")
    assert placement(LEFT_ONLY, ("R", 22)) == ("right:0;top:22%;--ox:100%;--oy:50%", -1, 1, "mid")
    assert placement(WHOLE, ("F", 2, 68)) == ("left:2%;top:68%;--ox:50%;--oy:50%", 1, 1, "mid")


@pytest.mark.parametrize("cuts, spec", [(TOP_ONLY, ("L", 20)), (LEFT_ONLY, ("T", 20)), (TOP_ONLY, ("TL",)), (CORNER, ("F", 1, 1))])
def test_art_refuses_a_spot_that_would_show_its_cut_side(cuts, spec):
    with pytest.raises(ValueError):
        placement(cuts, spec)


def test_every_screen_has_its_own_readable_color():
    colors = [screen["color"] for screen in SCREENS.values()]
    assert len(SCREENS) == 20
    assert len(set(colors)) == 20
    assert SCREENS["favIntro"]["color"] == "#6f2dff"
    for color in colors:
        assert contrast(text_color(color), color) >= 4.5, color


def test_no_art_repeats_on_back_to_back_screens():
    screens = list(SCREENS.values())
    for before, after in zip(screens, screens[1:]):
        assert not {piece[0] for piece in before["art"]} & {piece[0] for piece in after["art"]}


def test_purple_scribbles_stay_off_dark_screens():
    scribbles = {"maroon-01", "coral-01", "coral-05", "plum-02", "teal-01", "periwinkle-01"}
    for name, screen in SCREENS.items():
        if name != "home" and contrast(screen["color"], "#000000") < 6:  # home keeps its original art
            assert not scribbles & {piece[0] for piece in screen["art"]}, name


def test_chrome_stays_off_the_palest_screens():
    chrome = {"black-00", "plum-00", "maroon-04", "teal-00", "periwinkle-03"}
    for name in ("topups", "laundry"):
        assert not chrome & {piece[0] for piece in SCREENS[name]["art"]}, name


def test_screen_colors_are_generated_from_the_table():
    css = (ROOT / "static" / "styles" / "screens.css").read_text(encoding="utf8")
    for name, screen in SCREENS.items():
        assert f"section#{name} {{ --scene: {screen['color']}; --fg: {text_color(screen['color'])}; }}" in css
    assert "--scene: #" not in story_css()


def test_every_screen_has_art_from_its_row_in_the_table(client):  # noqa: F811
    html = page(client)
    for screen in re.findall(r"<section\b.*?</section>", html, re.S):
        assert '<div class="art" aria-hidden="true">' in screen, screen[:60]
    for sprite in re.findall(r'<span class="sprite.*?</span>', html, re.S):
        for needed in ('alt=""', 'loading="lazy"', "width=", "height="):
            assert needed in sprite
    home = html[html.index('<section id="home">'):html.index('id="favIntro"')]
    assert home.count('class="sprite') == len(SCREENS["home"]["art"])


def test_drawings_cut_by_the_frame_are_one_sprite_again():
    assert sum(len(group) - 1 for groups in JOINED.values() for group in groups) == 16
    assert len(list((ROOT / "static" / "styles" / "imgs" / "sprites").glob("*.png"))) == 29


def test_a_screen_never_shows_the_green_flower_twice():
    flowers = {"black-01", "maroon-05", "plum-01"}  # the same drawing, in three backgrounds
    for name, screen in SCREENS.items():
        assert len(flowers & {piece[0] for piece in screen["art"]}) <= 1, name

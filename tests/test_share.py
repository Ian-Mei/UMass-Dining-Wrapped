"""What the two share cards show, by meal plan."""
import json
import re
from pathlib import Path
from types import SimpleNamespace as Row

import pandas as pd

import app as app_module
from wrapped.personality import CONNOISSEUR, FRANK_FANATIC, HAMP_HEAD
from wrapped.share import share_card

from .conftest import charge, make_history_pdf, swipe
from .test_app import client, upload  # noqa: F401  (client is a fixture)

MEALS = ["Breakfast", "Lunch", "Dinner", "Late_Night", "GrabNGo", "Total"]


def table(**columns):
    return pd.DataFrame({name: pd.Series(values, index=MEALS, dtype=object) for name, values in columns.items()}, index=MEALS)


def person(plan="Unlimited", blue_wall=None, streak=4, places=3, vendors=None, halls=None, swipes=None):
    if vendors is None:
        vendors = pd.DataFrame({"spent": [30.4, 12.0, 5.0, 1.0]}, index=["Wasabi", "Tavola", "Peet's", "Yum"])
    return Row(
        meal_plan=plan,
        total_swipes=20,
        total_spent=48.4,
        places_tried=places,
        hall_ranking=[("Worcester", 9), ("Berk", 6), ("Hamp", 3), ("Frank", 2)] if halls is None else halls,
        vendors=vendors,
        swipes=table(
            Worcester=[1, 4, 2, 2, 0, 9],
            Berk=[0, 3, 2, 1, None, 6],
            Hamp=[1, 1, 1, None, None, 3],
            Frank=[0, 1, 1, None, 0, 2],
            **{"Harvest Market": [0, 3, 2, None, None, 5]},
        ) if swipes is None else swipes,
        highlights=Row(blue_wall=blue_wall, streak=Row(days=streak)),
    )


BLUE_WALL = Row(total=12, tried=3, of=9, spots=[Row(name="Wasabi", swipes=7), Row(name="Tavola", swipes=4), Row(name="Yum", swipes=1)])


def section(card, title):
    return next(s for s in card["sections"] if s["title"] == title)


def test_unlimited_compares_dining_halls_and_meals():
    card = share_card(person())
    assert card["plan"] == "Unlimited"
    assert [s["title"] for s in card["sections"]] == ["Top dining halls", "Meals", "Top spots"]
    assert section(card, "Top dining halls")["rows"][0] == ["Worcester", 9]
    assert section(card, "Meals")["rows"] == [["2", "breakfast"], ["9", "lunch"], ["6", "dinner"], ["3", "late night"]]


def test_ycmp_compares_blue_wall_and_harvest():
    card = share_card(person("YCMP", BLUE_WALL))
    assert [s["title"] for s in card["sections"]] == ["Blue Wall · 12 swipes", "Where the swipes went", "Top spots"]
    assert section(card, "Blue Wall · 12 swipes")["rows"][0] == ["Wasabi", 7]
    assert section(card, "Where the swipes went")["rows"] == [["12", "Blue Wall"], ["5", "Harvest"], ["20", "dining halls"], ["3/9", "BW spots"]]


def test_ycmp_without_blue_wall_falls_back_to_dining_halls():
    titles = [s["title"] for s in share_card(person("YCMP"))["sections"]]
    assert titles[0] == "Top dining halls"
    assert "Blue Wall" not in str(section(share_card(person("YCMP")), "Where the swipes went")["rows"])


def test_other_plans_show_dining_halls():
    assert share_card(person(None))["sections"][0]["title"] == "Top dining halls"


def test_top_spots_are_the_three_biggest_in_whole_dollars():
    assert section(share_card(person()), "Top spots")["rows"] == [["Wasabi", "$30"], ["Tavola", "$12"], ["Peet's", "$5"]]


def test_stats_leave_out_what_they_never_did():
    assert share_card(person())["stats"] == [["20", "swipes"], ["$48", "dollars"], ["3", "places"], ["4", "day streak"]]
    assert share_card(person(streak=0, places=0))["stats"] == [["20", "swipes"], ["$48", "dollars"]]
    assert ["1", "place"] in share_card(person(places=1))["stats"]


def test_sections_with_nothing_in_them_are_left_out():
    card = share_card(person(halls=[], vendors=pd.DataFrame(columns=["spent"]), swipes=table(Worcester=[0, 0, 0, 0, 0, 0])))
    assert card["sections"] == []


def test_results_page_has_both_cards_and_a_preview(client):  # noqa: F811
    html = upload(client, make_history_pdf([
        swipe("WorcDC2", "March 4, 2024, 12:00PM"),
        charge("Wasabi 1", "March 5, 2024, 1:00PM", 10.00),
    ])).get_data(as_text=True)
    card = html[html.index('id = "card"'):]
    assert 'class="face trading"' in card
    assert 'class="face receipt"' in card
    assert "YOU ORDERED" in card
    assert 'data-choice="receipt"' in card
    assert '<dialog class="sharedialog"' in html
    assert 'id="share-data"' in html
    assert re.search(r"family=Space\+Mono", html)


def test_the_page_behind_the_preview_cant_scroll():
    root = Path(__file__).parent.parent / "static"
    css = (root / "styles" / "story.css").read_text(encoding="utf8")
    assert "html:has(.sharedialog" not in css  # hiding the page's overflow makes it jump
    assert 'addEventListener("wheel", holdPage' in (root / "scripts" / "share-card.js").read_text(encoding="utf8")
    assert 'document.querySelector("dialog[open]")' in (root / "scripts" / "story.js").read_text(encoding="utf8")
    assert "if (blockedBehindDialog(event.key," in (root / "scripts" / "story.js").read_text(encoding="utf8")


def test_card_frames_are_measured_inside_the_card():
    css = (Path(__file__).parent.parent / "static" / "styles" / "story.css").read_text(encoding="utf8")
    # cqw on the container itself measures the window, so the frame belongs on the child.
    assert not re.search(r"\.face\.(trading|receipt) \{[^}]*padding", css)
    assert re.search(r"\.trading \.in \{[^}]*margin: 3\.2cqw", css)
    assert re.search(r"\.receipt \.in \{[^}]*margin: 2\.6cqw", css)
    assert "calc((60vw - 48px) * 16 / 9)" in css


def test_the_cards_and_preview_keep_their_own_look():
    css = (Path(__file__).parent.parent / "static" / "styles" / "story.css").read_text(encoding="utf8")
    assert re.search(r"\.face\.receipt, \.face\.receipt \* \{[^}]*Space Mono", css)  # wrapped.css sets a font on *
    assert re.search(r"\.sharedialog \{[^}]*margin: auto", css)                       # and removes every margin
    assert re.search(r"\.face \{[^}]*border: 3px solid", css)                         # visible on the same color


def page_with(people):
    result, _ = app_module.build_from_pdfs([make_history_pdf([swipe("WorcDC2", "March 4, 2024, 12:00PM")])])
    result.personalities = people
    result.reasons = {}
    with app_module.app.test_request_context():
        return app_module.render_wrapped(result)


def test_share_screen_lets_them_pick_any_of_their_personalities():
    html = page_with([FRANK_FANATIC, CONNOISSEUR, HAMP_HEAD])
    picker = html[html.index('class="personapick"'):html.index('class="cardswitch"')]
    assert picker.count("<button") == 3
    assert '<button type="button" data-name="Frank Fanatic" aria-pressed="true">' in picker
    assert '<button type="button" data-name="Connoisseur" aria-pressed="false">' in picker
    data = json.loads(re.search(r'id="share-data" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert data["personality"] == "Frank Fanatic"
    assert [p["name"] for p in data["personalities"]] == ["Frank Fanatic", "Connoisseur", "Hamp Head"]
    assert data["personalities"][1]["image"].endswith("personalities/connoisseur.png")


def test_one_personality_has_no_picker():
    assert 'class="personapick"' not in page_with([FRANK_FANATIC])


def test_browsing_the_wheel_carries_over_to_the_share_card():
    scripts = Path(__file__).parent.parent / "static" / "scripts"
    wheel = (scripts / "personality-wheel.js").read_text(encoding="utf8")
    assert 'if (browsing) root.dispatchEvent(new CustomEvent("personality-shown"' in wheel
    assert '"personality-shown"' in (scripts / "share-card.js").read_text(encoding="utf8")


def test_receipt_drawing_has_a_border():
    css = (Path(__file__).parent.parent / "static" / "styles" / "story.css").read_text(encoding="utf8")
    assert re.search(r"\.receipt \.hero img \{[^}]*border: \.6cqw solid #1c1c1c", css)


def test_meals_add_up_to_the_dining_hall_swipes():
    swipes = table(
        Worcester=[0, 1, 5, 0, 10, 16],  # Grab 'n Go gets its own tile
        Hamp=[0, 0, 1, None, None, 3],   # two swipes after 9pm at a hall with no late night
    )
    rows = section(share_card(person(swipes=swipes)), "Meals")["rows"]
    assert rows == [["0", "breakfast"], ["1", "lunch"], ["8", "dinner"], ["0", "late night"], ["10", "grab n go"]]
    assert sum(int(value) for value, _ in rows) == 19


def test_only_grab_n_go_still_shows_meals():
    swipes = table(Worcester=[0, 0, 0, 0, 4, 4])
    assert ["4", "grab n go"] in section(share_card(person(swipes=swipes)), "Meals")["rows"]


def test_harvest_means_harvest_market():
    swipes = table(**{"Harvest Market": [0, 3, 2, None, None, 5], "Harvest Cafe": [0, 1, 1, None, None, 2]})
    assert ["5", "Harvest"] in section(share_card(person("YCMP", BLUE_WALL, swipes=swipes)), "Where the swipes went")["rows"]


def test_controls_that_need_javascript_hide_without_it():
    css = (Path(__file__).parent.parent / "static" / "styles" / "story.css").read_text(encoding="utf8")
    assert "html:not(.js) .sharebtn, html:not(.js) .story-nav { display: none; }" in css


def test_receipt_ends_with_the_stamp():
    root = Path(__file__).parent.parent
    template = (root / "templates" / "_share_cards.html").read_text(encoding="utf8")
    script = (root / "static" / "scripts" / "share-card.js").read_text(encoding="utf8")
    assert "THANKS FOR EATING" not in template + script
    assert 'class="foot">UMASS DINING WRAPPED &middot; {{ semester|upper }}' in template

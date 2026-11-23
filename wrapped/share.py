"""The stats on the two share cards. YCMP plans choose where a swipe goes, so they compare Blue Wall
and Harvest; everyone else compares dining halls and meals."""
import re

from .highlights import HARVEST_MARKET
from .stats import HALL_ORDER


def _count(value):
    """A table cell as a number. None means the hall doesn't serve that meal."""
    return 0 if value is None or value != value else int(value)


def _plural(count, word):
    return word if count == 1 else f"{word}s"


def _total(wrapped, columns, row="Total"):
    return sum(_count(wrapped.swipes[column][row]) for column in columns)


def _halls_in(wrapped):
    return [hall for hall in HALL_ORDER if hall in wrapped.swipes.columns]


def _stats(wrapped):
    stats = [[str(wrapped.total_swipes), "swipes"], [f"${wrapped.total_spent:.0f}", "dollars"]]
    if wrapped.places_tried:
        stats.append([str(wrapped.places_tried), _plural(wrapped.places_tried, "place")])
    days = wrapped.highlights.streak.days
    if days:
        stats.append([str(days), "day streak"])
    return stats


def _hall_ranking(wrapped):
    rows = [[hall, int(visits)] for hall, visits in wrapped.hall_ranking[:4]]
    return {"title": "Top dining halls", "kind": "rank", "rows": rows}


def _meals(wrapped):
    halls = _halls_in(wrapped)
    breakfast, lunch, late, grab = (_total(wrapped, halls, row) for row in ("Breakfast", "Lunch", "Late_Night", "GrabNGo"))
    # Dinner is the rest, so a late swipe at a hall with no late night still counts somewhere.
    dinner = _total(wrapped, halls) - breakfast - lunch - late - grab
    rows = [[str(breakfast), "breakfast"], [str(lunch), "lunch"], [str(dinner), "dinner"], [str(late), "late night"]]
    if grab:
        rows.append([str(grab), "grab n go"])
    return {"title": "Meals", "kind": "tiles", "rows": rows if any(row[0] != "0" for row in rows) else []}


def _blue_wall(blue_wall):
    title = f"Blue Wall · {blue_wall.total} {_plural(blue_wall.total, 'swipe')}"
    return {"title": title, "kind": "rank", "rows": [[spot.name, int(spot.swipes)] for spot in blue_wall.spots[:4]]}


def _where_swipes_went(wrapped, blue_wall):
    harvest = _total(wrapped, [c for c in wrapped.swipes.columns if re.search(HARVEST_MARKET, str(c), re.IGNORECASE)])
    halls = _total(wrapped, _halls_in(wrapped))
    rows = []
    if blue_wall:
        rows.append([str(blue_wall.total), "Blue Wall"])
    if harvest:
        rows.append([str(harvest), "Harvest"])
    if halls:
        rows.append([str(halls), "dining halls"])
    if blue_wall:
        rows.append([f"{blue_wall.tried}/{blue_wall.of}", "BW spots"])
    return {"title": "Where the swipes went", "kind": "tiles", "rows": rows}


def _top_spots(wrapped):
    rows = [[str(name), f"${spent:.0f}"] for name, spent in wrapped.vendors["spent"].head(3).items()]
    return {"title": "Top spots", "kind": "list", "rows": rows}


def share_card(wrapped):
    """Plain data for the page and for drawing the saved image."""
    blue_wall = wrapped.highlights.blue_wall
    if wrapped.meal_plan == "YCMP":
        first = _blue_wall(blue_wall) if blue_wall else _hall_ranking(wrapped)
        second = _where_swipes_went(wrapped, blue_wall)
    else:
        first, second = _hall_ranking(wrapped), _meals(wrapped)
    sections = [first, second, _top_spots(wrapped)]
    return {
        "plan": wrapped.meal_plan,
        "stats": _stats(wrapped),
        "sections": [section for section in sections if section["rows"]],
    }

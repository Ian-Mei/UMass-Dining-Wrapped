"""Compute the Wrapped stats from a clean transactions frame (see transactions.clean)."""
from dataclasses import dataclass

import pandas as pd

from .highlights import Highlights, build_highlights, display_name
from .personality import Personality, pick_personality
from .transactions import GRAB_N_GO_HALLS, LATE_NIGHT_HALLS, ParseError

HALL_ORDER = ["Hamp", "Worcester", "Berk", "Frank"]

SWIPE_ROWS = ["Breakfast", "Lunch", "Dinner", "Late_Night", "GrabNGo", "Total"]


@dataclass
class Laundry:
    washes: int
    dries: int
    spent: float
    favorite_machine: str
    favorite_day: str


@dataclass
class Wrapped:
    semester: str        # "Spring 2024"
    semester_short: str  # "Spring 24"
    start: pd.Timestamp
    end: pd.Timestamp
    # Rows are SWIPE_ROWS; columns are the four dining halls followed by any other
    # places meal swipes were used. None means "not offered there".
    swipes: pd.DataFrame
    # Dining halls with at least one visit, most visited first: [(name, visits)].
    hall_ranking: list
    # Index is the vendor; columns breakfast, lunch, dinner, visits, spent. Most spent first.
    vendors: pd.DataFrame
    total_swipes: int
    total_spent: float
    laundry: Laundry | None
    highlights: Highlights
    personality: Personality

    @property
    def favorite_hall(self):
        return self.hall_ranking[0][0] if self.hall_ranking else None


def meal_period(timestamps: pd.Series) -> pd.Series:
    minutes = timestamps.dt.hour * 60 + timestamps.dt.minute
    period = pd.Series("Dinner", index=timestamps.index)
    period[minutes < 16 * 60 + 30] = "Lunch"
    period[minutes < 11 * 60] = "Breakfast"
    # Late night runs past midnight, so a 12:30am swipe isn't breakfast.
    period[(minutes >= 21 * 60) | (minutes < 4 * 60)] = "Late_Night"
    return period


def semester_name(timestamps: pd.Series) -> tuple[str, str]:
    middle = timestamps.sort_values().iloc[len(timestamps) // 2]
    season = "Fall" if middle.month >= 8 else "Spring" if middle.month <= 5 else "Summer"
    return f"{season} {middle.year}", f"{season} {middle.year % 100:02d}"


def swipe_column(visits: pd.DataFrame, late_night: bool, grab_n_go: bool) -> dict:
    # Counts swipes, not rows: GET sometimes takes 2 in one row (e.g. paying for a friend).
    is_grab = visits["grab_n_go"] if grab_n_go else pd.Series(False, index=visits.index)
    periods = visits[~is_grab].groupby("period")["amount"].sum()
    return {
        "Breakfast": int(periods.get("Breakfast", 0)),
        "Lunch": int(periods.get("Lunch", 0)),
        "Dinner": int(periods.get("Dinner", 0)),
        # Places without late night only count those swipes toward the total.
        "Late_Night": int(periods.get("Late_Night", 0)) if late_night else None,
        "GrabNGo": int(visits.loc[is_grab, "amount"].sum()) if grab_n_go else None,
        "Total": int(visits["amount"].sum()),
    }


def vendor_name(place: str) -> str:
    return display_name(place, None, False)


def swipe_table(tx: pd.DataFrame) -> pd.DataFrame:
    # Only swipes: dining dollars paid at a hall count toward money spent, not meal swipes.
    halls = tx[(tx["kind"] == "hall") & tx["is_swipe"]]
    columns = {
        hall: swipe_column(halls[halls["hall"] == hall], hall in LATE_NIGHT_HALLS, hall in GRAB_N_GO_HALLS)
        for hall in HALL_ORDER
    }
    # Meal swipes used somewhere other than a dining hall (e.g. a cafe meal exchange).
    other = tx[(tx["kind"] == "vendor") & tx["is_swipe"]]
    for place, visits in other.groupby(other["place"].map(vendor_name), sort=False):
        columns[place] = swipe_column(visits, late_night=False, grab_n_go=False)
    # Build object columns one at a time so pandas keeps ints and None instead of floats and NaN.
    return pd.DataFrame({name: pd.Series(col, dtype=object) for name, col in columns.items()}, index=SWIPE_ROWS)


def vendor_table(tx: pd.DataFrame) -> pd.DataFrame:
    # Top-ups went with a meal swipe, so they aren't a separate trip to that place.
    paid = tx[(tx["kind"] == "vendor") & ~tx["is_swipe"] & ~tx["is_top_up"]]
    columns = ["breakfast", "lunch", "dinner", "visits", "spent"]
    if paid.empty:
        return pd.DataFrame(columns=columns)
    grouped = paid.groupby(paid["place"].map(vendor_name))
    table = pd.DataFrame({
        "breakfast": grouped["period"].agg(lambda p: int((p == "Breakfast").sum())),
        "lunch": grouped["period"].agg(lambda p: int((p == "Lunch").sum())),
        # Vendors don't have a separate late night, so it counts as dinner.
        "dinner": grouped["period"].agg(lambda p: int(p.isin(["Dinner", "Late_Night"]).sum())),
        "visits": grouped.size(),
        "spent": grouped["amount"].sum(),
    })
    return table.sort_values(["spent", "visits"], ascending=False)


def laundry_stats(tx: pd.DataFrame) -> Laundry | None:
    loads = tx[tx["kind"] == "laundry"]
    if loads.empty:
        return None
    machine = loads["location"].str.replace(r"^X\s*-\s*", "", regex=True)
    return Laundry(
        washes=int(loads["place"].str.contains("WASHER").sum()),
        dries=int(loads["place"].str.contains("DRYER").sum()),
        spent=float(loads["amount"].sum()),
        favorite_machine=machine.value_counts().idxmax(),
        favorite_day=loads["timestamp"].dt.day_name().value_counts().idxmax(),
    )


def build_wrapped(tx: pd.DataFrame, today=None, history=None) -> Wrapped:
    """today: the date plan pace counts up to (defaults to the real date).
    history: every account's balance history (transactions.account_history), so plan pace sees
    accounts nothing has been bought with yet."""
    if tx.empty:
        raise ParseError("Couldn't find any purchases in that history. Make sure it covers a semester you were on campus.")
    tx = tx.assign(period=meal_period(tx["timestamp"]))

    swipes = swipe_table(tx)
    totals = swipes.loc["Total", HALL_ORDER].astype(int).sort_values(ascending=False, kind="stable")
    vendors = vendor_table(tx)
    semester, semester_short = semester_name(tx["timestamp"])

    wrapped = Wrapped(
        semester=semester,
        semester_short=semester_short,
        start=tx["timestamp"].min(),
        end=tx["timestamp"].max(),
        swipes=swipes,
        hall_ranking=[(hall, int(n)) for hall, n in totals.items() if n > 0],
        vendors=vendors,
        total_swipes=int(swipes.loc["Total"].sum()),
        total_spent=float(tx.loc[tx["kind"].isin(["hall", "vendor"]) & ~tx["is_swipe"], "amount"].sum()),
        laundry=laundry_stats(tx),
        highlights=build_highlights(tx, semester, today, history),
        personality=None,
    )
    wrapped.personality = pick_personality(wrapped)
    return wrapped

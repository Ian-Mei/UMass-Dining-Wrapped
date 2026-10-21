"""The extra Wrapped highlights: plan pace, routine, streak calendar, clock and fun facts.

Each one gets its own screen on the results page (see templates/wrapped.html).
"""
import re
from dataclasses import dataclass
from datetime import date, time, timedelta

import pandas as pd

from .transactions import GRAB_N_GO_HALLS

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FOOD = ["hall", "vendor"]
# Roughly the last day of finals, for "will your plan last?" projections.
SEMESTER_ENDS = {"Fall": (12, 18), "Spring": (5, 15), "Summer": (8, 15)}
# Where the bookmarklet starts downloading each semester (see static/scripts/history_windows.js).
SEMESTER_STARTS = {"Fall": (8, 15), "Spring": (1, 15), "Summer": (5, 16)}
MIN_PLAN_CHARGES = 5
# Only project plans still in use, not e.g. a staff training account from the first week.
MAX_PLAN_IDLE_DAYS = 21
MIN_ROUTINE_REPEATS = 3
MIN_BLUE_WALL_SWIPES = 3
MIN_HARVEST_SWIPES = 5
MIN_TOP_UPS = 3
TOP_UP_PLACES_SHOWN = 3
DOUBLE_SWIPE_SECONDS = 120
# Like meal_period's late night: anything before 4am belongs to the night before.
NIGHT_ENDS_HOUR = 4


@dataclass
class PlanPace:
    label: str        # "Meal Swipes", "Dining Dollars", or the account name
    account: str
    is_meals: bool
    used: float
    left: float
    per_week: float
    runs_out: date | None  # None if it lasts the semester at this pace
    left_at_end: float     # projected left on semester_end (what was left, if it's already over)
    semester_end: date


@dataclass
class Routine:
    name: str
    weekday: str
    period: str  # "breakfast", "lunch", "dinner" or "late night"
    times: int


@dataclass
class Streak:
    days: int
    start: date | None
    end: date | None


@dataclass
class Day:
    day: date
    count: int
    in_range: bool
    in_streak: bool

    @property
    def level(self):
        return min(self.count, 4)


@dataclass
class Calendar:
    weeks: list  # list of weeks, each 7 Days from Sunday to Saturday

    @property
    def month_labels(self):
        """Month name over the first week and over each week where a month starts."""
        labels = []
        for i, week in enumerate(self.weeks):
            starts = [d.day for d in week if d.in_range and (d.day.day == 1 or i == 0)]
            labels.append(starts[0].strftime("%b") if starts else "")
        return labels


@dataclass
class Clock:
    typical_lunch: time | None
    earliest: time
    latest: time
    top_day: str
    top_day_count: int
    quiet_day: str
    quiet_day_count: int
    hours: list  # hours of the day shown in grid; past midnight is 24, 25, ...
    grid: dict   # weekday -> {hour: purchases}
    max_count: int

    def level(self, count):
        return 0 if not count else max(1, round(4 * count / self.max_count))


@dataclass
class FunFacts:
    double_swipes: int
    places_tried: int
    busiest_day: date
    busiest_day_count: int
    busiest_day_places: list


@dataclass
class Highlights:
    plans: list
    routine: Routine | None
    streak: Streak
    calendar: Calendar
    clock: Clock
    fun: FunFacts
    blue_wall: "BlueWall | None"
    harvest: "Harvest | None"
    top_ups: "TopUps | None"
    explorer: "Explorer"
    raw_sections: list


def display_name(place: str, hall, grab_n_go: bool) -> str:
    """'CPOS Worcester GG' -> "Worcester Grab 'n Go", 'CPOS ISB CafÃ©' -> 'ISB Café'."""
    if isinstance(hall, str):
        return f"{hall} Grab 'n Go" if grab_n_go else hall
    name = re.sub(r"^CPOS\s+", "", place)
    try:
        # GET's text sometimes comes through as UTF-8 read as Latin-1.
        name = name.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return name


def build_highlights(tx: pd.DataFrame, semester: str, today: date | None = None, history=None) -> Highlights:
    """tx is a clean transactions frame with a period column (see stats.build_wrapped)."""
    season, year = semester.split()
    semester_start = date(int(year), *SEMESTER_STARTS[season])
    semester_end = date(int(year), *SEMESTER_ENDS[season])
    as_of = tx["timestamp"].max().date()
    # Plan pace counts up to today, so days without buying anything slow it down. Run after the
    # semester (e.g. over winter break), it stops at the semester's end.
    pace_until = min(today or date.today(), semester_end)

    food = tx[tx["kind"].isin(FOOD)].copy()
    # An unreadable amount is still one swipe (as in the swipe table), or $0.
    food["amount"] = food["amount"].fillna(food["is_swipe"].astype(float))
    food["name"] = [display_name(p, h, g) for p, h, g in zip(food["place"], food["hall"], food["grab_n_go"])]
    food["spot"] = food["hall"].where(food["hall"].notna(), food["name"])
    night = food["timestamp"] - pd.Timedelta(hours=NIGHT_ENDS_HOUR)
    food["day"] = night.dt.date
    food["weekday"] = night.dt.day_name()
    food["hour"] = food["timestamp"].dt.hour.where(food["timestamp"].dt.hour >= NIGHT_ENDS_HOUR,
                                                   food["timestamp"].dt.hour + 24)

    # A top-up is part of its swipe, not another trip, so it doesn't count as a visit.
    visits = food[~food["is_top_up"]]
    streak = longest_streak(visits["day"])
    return Highlights(
        plans=plan_paces(tx, pace_until, semester_start, semester_end, history),
        routine=top_routine(visits),
        streak=streak,
        calendar=calendar(visits, as_of, streak),
        clock=clock(visits),
        fun=fun_facts(visits),
        blue_wall=blue_wall(visits),
        harvest=harvest(visits),
        top_ups=top_ups(food),
        explorer=explorer(food),
        raw_sections=raw_sections(food),
    )


def plan_paces(tx, until, semester_start, semester_end, history=None) -> list:
    """Each plan's pace from its first charge up to until, projected on to semester_end.

    All dining-dollar accounts are one plan: RAs get two, an RA one GET spends first and a
    regular one that sits untouched until then, and both are theirs to spend. history (see
    transactions.account_history) has every account, including ones nothing has been bought
    with yet; without it, what's left comes from the last purchase on each account.
    """
    history = history or {}
    # Only this semester's purchases, in case the upload also covers an earlier one.
    tx = tx[tx["timestamp"].dt.date >= semester_start].sort_values("timestamp")
    plans = []
    for plan, charges in tx.groupby(tx["account"].map(plan_name)):
        accounts = sorted(charges["account"].unique())
        dining_dollars = plan == DINING_DOLLARS
        # Skip unlimited plans, accounts mostly used for laundry, and balances that don't count down.
        if (len(charges) < MIN_PLAN_CHARGES or "unlimited" in plan.lower()
                or charges["kind"].isin(FOOD).mean() < 0.5
                or (until - charges["timestamp"].iloc[-1].date()).days > MAX_PLAN_IDLE_DAYS
                or not (dining_dollars or charges["balance"].iloc[-1] < charges["balance"].iloc[0])):
            continue
        is_meals = bool(charges["is_swipe"].iloc[0])
        used = float(charges["amount"].sum())
        if not used > 0:
            continue
        if dining_dollars:
            # Plus dining-dollar accounts with no purchases yet, if they're from this semester
            # (not, say, last year's RA account still in an older upload).
            accounts = sorted(set(accounts) | {
                a for a, rows in history.items()
                if plan_name(a) == DINING_DOLLARS and any(semester_start <= when.date() <= until for when, _, _ in rows)
            })
        last_charge = charges.groupby("account")["balance"].last()
        left = float(sum(balance_on(history.get(a), until, last_charge.get(a, 0)) for a in accounts))
        per_day = used / max((until - charges["timestamp"].iloc[0].date()).days, 1)

        runs_out = None
        days_to_end = (semester_end - until).days
        if days_to_end <= 0:
            left_at_end = left
        elif left / per_day < days_to_end:
            runs_out, left_at_end = until + timedelta(days=left / per_day), 0
        else:
            left_at_end = left - per_day * days_to_end

        plans.append(PlanPace(
            label=plan if dining_dollars else ("Meal Swipes" if is_meals else plan),
            account=" + ".join(accounts),
            is_meals=is_meals,
            used=used,
            left=int(left) if is_meals else left,
            per_week=per_day * 7,
            runs_out=runs_out,
            left_at_end=round(left_at_end) if is_meals else round(left_at_end, 2),
            semester_end=semester_end,
        ))
    return sorted(plans, key=lambda p: (not p.is_meals, -p.used))


DINING_DOLLARS = "Dining Dollars"


def balance_on(rows, day, fallback):
    """An account's balance at the end of day, from its account_history rows (fallback if none).

    Rows after it don't count: over winter break the fall history can already have a Dec 20 row
    clearing unused swipes, but what was left at the end of fall is the balance before that.
    """
    before = [balance for when, _, balance in rows or [] if when.date() <= day]
    return before[-1] if before else fallback


def plan_name(account: str) -> str:
    """'UMass Dining Dollars' and 'RA/PM Dining Dollars 26-27' are both just Dining Dollars."""
    return DINING_DOLLARS if "dining dollars" in account.lower() else account


def top_routine(food) -> Routine | None:
    if food.empty:
        return None
    counts = food.groupby(["name", "weekday", "period"]).size().sort_values(ascending=False, kind="stable")
    (name, weekday, period), times = counts.index[0], int(counts.iloc[0])
    if times < MIN_ROUTINE_REPEATS:
        return None
    return Routine(name, weekday, period.replace("_", " ").lower(), times)


def longest_streak(days) -> Streak:
    best = Streak(0, None, None)
    run_start = prev = None
    for day in sorted(set(days)):
        if prev is None or (day - prev).days != 1:
            run_start = day
        prev = day
        length = (day - run_start).days + 1
        if length > best.days:
            best = Streak(length, run_start, day)
    return best


def calendar(food, as_of, streak) -> Calendar:
    if food.empty:
        return Calendar([])
    counts = food["day"].value_counts()
    start = min(food["day"])
    first = start - timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    last = as_of + timedelta(days=(5 - as_of.weekday()) % 7)    # on to Saturday
    days = []
    d = first
    while d <= last:
        days.append(Day(
            day=d,
            count=int(counts.get(d, 0)),
            in_range=start <= d <= as_of,
            in_streak=bool(streak.days) and streak.start <= d <= streak.end,
        ))
        d += timedelta(days=1)
    return Calendar([days[i:i + 7] for i in range(0, len(days), 7)])


def clock(food) -> Clock | None:
    if food.empty:
        return None
    minutes = food["hour"] * 60 + food["timestamp"].dt.minute
    lunch = minutes[food["period"] == "Lunch"]
    as_time = lambda m: time(int(m) // 60 % 24, int(m) % 60)  # noqa: E731
    by_day = food["weekday"].value_counts().reindex(WEEKDAYS, fill_value=0)
    busiest, quietest = by_day.idxmax(), by_day[::-1].idxmin()
    hours = list(range(int(food["hour"].min()), int(food["hour"].max()) + 1))
    cells = food.groupby(["weekday", "hour"]).size()
    grid = {day: {h: int(cells.get((day, h), 0)) for h in hours} for day in WEEKDAYS}
    return Clock(
        typical_lunch=as_time(lunch.median()) if len(lunch) else None,
        earliest=as_time(minutes[food["hour"] < 24].min() if (food["hour"] < 24).any() else minutes.min()),
        latest=as_time(minutes.max()),
        top_day=busiest,
        top_day_count=int(by_day[busiest]),
        quiet_day=quietest,
        quiet_day_count=int(by_day[quietest]),
        hours=hours,
        grid=grid,
        max_count=int(cells.max()),
    )


def fun_facts(food) -> FunFacts | None:
    if food.empty:
        return None
    swipes = food[food["is_swipe"]].sort_values("timestamp")
    gap = swipes["timestamp"].diff().dt.total_seconds()
    same_place = swipes["location"].eq(swipes["location"].shift())
    by_day = food["day"].value_counts().sort_index()
    busiest = by_day.idxmax()
    that_day = food[food["day"] == busiest].sort_values("timestamp")
    return FunFacts(
        # Two swipes back to back at one place, or one row that took 2 or more.
        double_swipes=int((same_place & (gap <= DOUBLE_SWIPE_SECONDS)).sum() + (swipes["amount"] - 1).clip(lower=0).sum()),
        places_tried=int(food["spot"].nunique()),
        busiest_day=busiest,
        busiest_day_count=int(by_day[busiest]),
        busiest_day_places=list(dict.fromkeys(that_day["name"])),
    )


# Blue Wall, the Campus Center food court. Harvest Market is next door but separate, and so is
# Peet's. Matched loosely because GET's names vary ("Yum Bakery", "CPOS Tamales").
BLUE_WALL = {
    "Tavola": r"\btavola\b",
    "Tamales": r"\btamales\b",
    "Wasabi": r"\bwasabi\b",
    "Star Ginger": r"\bstar ginger\b",
    "Green Fields": r"\bgreen fields\b",
    "Deli Delish": r"\bdeli delish\b",
    "Yum! Bakery": r"\byum\b",
    "People's Organic Coffee": r"\bpeople'?s organic\b",
    "Paciugo": r"\bpaciugo\b",
}
HARVEST_MARKET = r"\bharvest market\b"

# One line about your top spot. {n} is the swipe count and {s} pluralizes the word before it;
# {t} and {ts} are the same for trips there (a row can take 2 swipes but it's still one trip).
REMARKS = {
    "Tavola": "{n} swipe{s} of pizza, pasta and hummus bowls. Tavola is basically your Italian grandma now.",
    "Tamales": "{n} burrito{s} deep. Those house-made tortillas have a hold on you.",
    "Wasabi": "{n} round{s} of sushi and teppanyaki. You're on a first-name basis with the miso soup.",
    "Star Ginger": "{n} bowl{s} of pho and bibimbap. Star Ginger is your comfort food and we respect it.",
    "Green Fields": "{n} custom salad{s} and wraps. Somebody's actually eating their greens.",
    "Deli Delish": "{n} grinder{s} and hot-pressed sandwiches. Deli Delish should name one after you.",
    "Yum! Bakery": "{n} swipe{s} on cookies, cakes and macarons. Dessert counts as a meal if you swipe for it.",
    "People's Organic Coffee": "{t} coffee run{ts}. People's Organic is basically fueling your GPA.",
    "Paciugo": "{t} trip{ts} for gelato. It's always gelato weather if you believe hard enough.",
}
HARVEST_REMARK = "{t} trip{ts} to the hot bar. The Harvest Market staff probably know your order before you do."


@dataclass
class BlueWallSpot:
    name: str
    swipes: int
    share: float  # swipes as a fraction of the top spot's, for the bar chart
    place: str = ""  # the same place as the explorer names it (GET's spelling, e.g. "Yum Bakery")


@dataclass
class BlueWall:
    spots: list  # BlueWallSpots, most swipes first (ties: most recent visit first)
    total: int
    remark: str
    of: int = len(BLUE_WALL)

    @property
    def top(self):
        return self.spots[0]

    @property
    def tried(self):
        return len(self.spots)


@dataclass
class Harvest:
    swipes: int
    remark: str
    place: str  # as Explore your places names it, for the "See every visit" link


@dataclass
class TopUpPlace:
    name: str
    count: int
    average: float


@dataclass
class TopUps:
    count: int
    total: float
    places: list  # TopUpPlaces, most top-ups first


def blue_wall_name(name: str) -> str | None:
    for spot, pattern in BLUE_WALL.items():
        if re.search(pattern, name, re.IGNORECASE):
            return spot
    return None


def remark(template: str, swipes: int, trips: int) -> str:
    return template.format(n=swipes, s="" if swipes == 1 else "s", t=trips, ts="" if trips == 1 else "s")


def by_count_then_recent(rows, key, swipes=False):
    """Group rows by key: [(key, count)] with the most first, and ties going to the most recent.

    swipes counts meal swipes rather than rows (a row can take 2).
    """
    grouped = rows.groupby(key).agg(n=("amount", "sum") if swipes else ("timestamp", "size"), last=("timestamp", "max"))
    grouped = grouped.sort_values(["n", "last"], ascending=False)
    return [(name, int(n)) for name, n in grouped["n"].items()]


def vendor_swipes(food):
    return food[(food["kind"] == "vendor") & food["is_swipe"]]


def blue_wall(food) -> BlueWall | None:
    swipes = vendor_swipes(food).assign(blue_wall=lambda f: f["name"].map(blue_wall_name)).dropna(subset=["blue_wall"])
    total = int(swipes["amount"].sum())
    if total < MIN_BLUE_WALL_SWIPES:
        return None
    counts = by_count_then_recent(swipes, "blue_wall", swipes=True)
    most = counts[0][1]
    places = swipes.groupby("blue_wall")["spot"].agg(lambda spots: spots.value_counts().index[0])
    spots = [BlueWallSpot(name, n, n / most, places[name]) for name, n in counts]
    top = spots[0].name
    return BlueWall(spots=spots, total=total,
                    remark=remark(REMARKS[top], spots[0].swipes, int((swipes["blue_wall"] == top).sum())))


def harvest(food) -> Harvest | None:
    swipes = vendor_swipes(food)
    there = swipes[swipes["name"].str.contains(HARVEST_MARKET, case=False, regex=True)]
    n = int(there["amount"].sum())
    if n < MIN_HARVEST_SWIPES:
        return None
    return Harvest(swipes=n, remark=remark(HARVEST_REMARK, n, len(there)), place=there["spot"].value_counts().index[0])


def top_ups(food) -> TopUps | None:
    ups = food[food["is_top_up"]]
    if len(ups) < MIN_TOP_UPS:
        return None
    places = [
        TopUpPlace(name, n, float(ups.loc[ups["name"] == name, "amount"].mean()))
        for name, n in by_count_then_recent(ups, "name")[:TOP_UP_PLACES_SHOWN]
    ]
    return TopUps(count=len(ups), total=float(ups["amount"].sum()), places=places)


# Explore your days / Explore your places (the last two screens; drawn by static/scripts/explorer.js).
MIN_PATTERN_VISITS = 5
PERIOD_WORDS = {"Breakfast": "around breakfast", "Lunch": "around lunch", "Dinner": "around dinner",
                "Late_Night": "late at night"}


@dataclass
class Explorer:
    purchases: list  # every food purchase, oldest first: {day, time, place, swipes, dollars, top_up}
    places: list     # {name, visits, swipes, note}, most visits first


def explorer(food) -> Explorer:
    food = food.sort_values("timestamp")
    purchases = [
        {
            "day": row.day.isoformat(),
            "time": f"{row.timestamp:%I:%M %p}".lstrip("0"),
            "place": row.name,
            "spot": row.spot,  # the place it's listed under in Explore your places and the raw data
            "swipes": int(row.amount) if row.is_swipe else 0,
            "dollars": 0 if row.is_swipe else round(float(row.amount), 2),
            "top_up": bool(row.is_top_up),
        }
        for row in food.itertuples()
    ]
    visits = food[~food["is_top_up"]]
    places = [
        {
            "name": spot,
            "visits": n,
            "swipes": int(visits.loc[(visits["spot"] == spot) & visits["is_swipe"], "amount"].sum()),
            "note": pattern_note(visits[visits["spot"] == spot]),
        }
        for spot, n in by_count_then_recent(visits, "spot")
    ]
    return Explorer(purchases, places)


def pattern_note(visits) -> str | None:
    """'Mostly Mondays and Tuesdays, usually around dinner.' when visits to a place have a pattern."""
    if len(visits) < MIN_PATTERN_VISITS:
        return None
    days = visits["weekday"].value_counts()
    top_two = days.index[:2]
    if days.iloc[0] / len(visits) > 0.5:
        when = f"Mostly {days.index[0]}s"
    elif days.iloc[:2].sum() / len(visits) >= 0.6:
        first, second = sorted(top_two, key=WEEKDAYS.index)
        when = f"Mostly {first}s and {second}s"
    else:
        when = None
    periods = visits["period"].value_counts()
    meal = PERIOD_WORDS[periods.index[0]] if periods.iloc[0] / len(visits) >= 0.6 else None
    if when and meal:
        return f"{when}, usually {meal}."
    if when:
        return f"{when}."
    if meal:
        return f"Usually {meal}."
    return None


# "All your data": every place's swipes and dining dollars, in sections.
HALL_COLUMNS = ["Breakfast", "Lunch", "Dinner", "Late night", "Grab 'n Go", "Swipes", "Dollars"]
PLACE_COLUMNS = ["Breakfast", "Lunch", "Dinner", "Swipes", "Dollars"]


def raw_sections(food) -> list:
    """[{title, columns, rows}] for dining halls, Blue Wall, Harvest Market and everywhere else.

    Each row is a place (food's spot, so a dining hall includes its Grab 'n Go): visits by meal,
    total swipes, and every dining dollar spent there (top-ups too), so the sections add up to the
    Wrapped's totals. Empty sections are left out.
    """
    def section(rows) -> str:
        if isinstance(rows.iloc[0]["hall"], str):
            return "Dining halls"
        name = rows.iloc[0]["name"]
        if blue_wall_name(name):
            return "Blue Wall"
        if re.search(HARVEST_MARKET, name, re.IGNORECASE):
            return "Harvest Market"
        return "Everywhere else"

    groups = {}
    for spot, rows in food.groupby("spot"):
        visits = rows[~rows["is_top_up"]]  # a top-up goes with its swipe, not a visit of its own
        is_grab = visits["grab_n_go"] & visits["hall"].isin(GRAB_N_GO_HALLS)
        meals = visits[~is_grab]["period"].value_counts()
        title = section(rows)
        row = {
            "place": spot,
            "Breakfast": int(meals.get("Breakfast", 0)),
            "Lunch": int(meals.get("Lunch", 0)),
            "Dinner": int(meals.get("Dinner", 0)),
        }
        if title == "Dining halls":
            row["Late night"] = int(meals.get("Late_Night", 0))
            row["Grab 'n Go"] = int(is_grab.sum())
        else:
            row["Dinner"] += int(meals.get("Late_Night", 0))  # vendors don't have a separate late night
        row["Swipes"] = int(rows.loc[rows["is_swipe"], "amount"].sum())
        row["Dollars"] = round(float(rows.loc[~rows["is_swipe"], "amount"].sum()), 2)
        groups.setdefault(title, []).append(row)

    order = ["Dining halls", "Blue Wall", "Harvest Market", "Everywhere else"]
    return [
        {
            "title": title,
            "columns": HALL_COLUMNS if title == "Dining halls" else PLACE_COLUMNS,
            "rows": sorted(groups[title], key=lambda r: (-r["Swipes"], -r["Dollars"], r["place"])),
        }
        for title in order if title in groups
    ]

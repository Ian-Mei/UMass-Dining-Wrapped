"""The extra Wrapped highlights: plan pace, routine, streak calendar, clock and fun facts.

Each one gets its own screen on the results page (see templates/wrapped.html).
"""
import re
from dataclasses import dataclass
from datetime import date, time, timedelta

import pandas as pd

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FOOD = ["hall", "vendor"]
# Roughly the last day of finals, for "will your plan last?" projections.
SEMESTER_ENDS = {"Fall": (12, 18), "Spring": (5, 15), "Summer": (8, 15)}
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


def build_highlights(tx: pd.DataFrame, semester: str) -> Highlights:
    """tx is a clean transactions frame with a period column (see stats.build_wrapped)."""
    season, year = semester.split()
    semester_end = date(int(year), *SEMESTER_ENDS[season])
    as_of = tx["timestamp"].max().date()

    food = tx[tx["kind"].isin(FOOD)].copy()
    food["name"] = [display_name(p, h, g) for p, h, g in zip(food["place"], food["hall"], food["grab_n_go"])]
    food["spot"] = food["hall"].where(food["hall"].notna(), food["name"])
    night = food["timestamp"] - pd.Timedelta(hours=NIGHT_ENDS_HOUR)
    food["day"] = night.dt.date
    food["weekday"] = night.dt.day_name()
    food["hour"] = food["timestamp"].dt.hour.where(food["timestamp"].dt.hour >= NIGHT_ENDS_HOUR,
                                                   food["timestamp"].dt.hour + 24)

    streak = longest_streak(food["day"])
    return Highlights(
        plans=plan_paces(tx, as_of, semester_end),
        routine=top_routine(food),
        streak=streak,
        calendar=calendar(food, as_of, streak),
        clock=clock(food),
        fun=fun_facts(food),
        blue_wall=blue_wall(food),
        harvest=harvest(food),
        top_ups=top_ups(food),
    )


def plan_paces(tx, as_of, semester_end) -> list:
    plans = []
    for account, charges in tx.sort_values("timestamp").groupby("account"):
        # Skip unlimited plans, accounts mostly used for laundry, and balances that don't count down.
        if (len(charges) < MIN_PLAN_CHARGES or "unlimited" in account.lower()
                or charges["kind"].isin(FOOD).mean() < 0.5
                or (as_of - charges["timestamp"].iloc[-1].date()).days > MAX_PLAN_IDLE_DAYS
                or not charges["balance"].iloc[-1] < charges["balance"].iloc[0]):
            continue
        is_meals = bool(charges["is_swipe"].iloc[0])
        used = float(charges["amount"].sum())
        if not used > 0:
            continue
        left = float(charges["balance"].iloc[-1])
        per_day = used / max((as_of - charges["timestamp"].iloc[0].date()).days, 1)

        runs_out = None
        days_to_end = (semester_end - as_of).days
        if days_to_end <= 0:
            left_at_end = left
        elif left / per_day < days_to_end:
            runs_out, left_at_end = as_of + timedelta(days=left / per_day), 0
        else:
            left_at_end = left - per_day * days_to_end

        if "dining dollars" in account.lower():
            label = "Dining Dollars"
        else:
            label = "Meal Swipes" if is_meals else account
        plans.append(PlanPace(
            label=label,
            account=account,
            is_meals=is_meals,
            used=used,
            left=int(left) if is_meals else left,
            per_week=per_day * 7,
            runs_out=runs_out,
            left_at_end=round(left_at_end) if is_meals else round(left_at_end, 2),
            semester_end=semester_end,
        ))
    return sorted(plans, key=lambda p: (not p.is_meals, -p.used))


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
        double_swipes=int((same_place & (gap <= DOUBLE_SWIPE_SECONDS)).sum()),
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

# One line about your top spot. {n} is the swipe count and {s} pluralizes the word before it.
REMARKS = {
    "Tavola": "{n} swipe{s} of pizza, pasta and hummus bowls. Tavola is basically your Italian grandma now.",
    "Tamales": "{n} burrito{s} deep. Those house-made tortillas have a hold on you.",
    "Wasabi": "{n} round{s} of sushi and teppanyaki. You're on a first-name basis with the miso soup.",
    "Star Ginger": "{n} bowl{s} of pho and bibimbap. Star Ginger is your comfort food and we respect it.",
    "Green Fields": "{n} custom salad{s} and wraps. Somebody's actually eating their greens.",
    "Deli Delish": "{n} grinder{s} and hot-pressed sandwiches. Deli Delish should name one after you.",
    "Yum! Bakery": "{n} swipe{s} on cookies, cakes and macarons. Dessert counts as a meal if you swipe for it.",
    "People's Organic Coffee": "{n} coffee run{s}. People's Organic is basically fueling your GPA.",
    "Paciugo": "{n} trip{s} for gelato. It's always gelato weather if you believe hard enough.",
}
HARVEST_REMARK = "{n} trip{s} to the hot bar. The Harvest Market staff probably know your order before you do."


@dataclass
class BlueWallSpot:
    name: str
    swipes: int
    share: float  # swipes as a fraction of the top spot's, for the bar chart


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


def remark(template: str, n: int) -> str:
    return template.format(n=n, s="" if n == 1 else "s")


def by_count_then_recent(rows, key):
    """Group rows by key: [(key, count)] with the most first, and ties going to the most recent."""
    grouped = rows.groupby(key)["timestamp"].agg(["size", "max"])
    grouped = grouped.sort_values(["size", "max"], ascending=False)
    return [(name, int(n)) for name, n in grouped["size"].items()]


def vendor_swipes(food):
    return food[(food["kind"] == "vendor") & food["is_swipe"]]


def blue_wall(food) -> BlueWall | None:
    swipes = vendor_swipes(food).assign(spot=lambda f: f["name"].map(blue_wall_name)).dropna(subset=["spot"])
    if len(swipes) < MIN_BLUE_WALL_SWIPES:
        return None
    counts = by_count_then_recent(swipes, "spot")
    most = counts[0][1]
    spots = [BlueWallSpot(name, n, n / most) for name, n in counts]
    return BlueWall(spots=spots, total=len(swipes), remark=remark(REMARKS[spots[0].name], spots[0].swipes))


def harvest(food) -> Harvest | None:
    swipes = vendor_swipes(food)
    n = int(swipes["name"].str.contains(HARVEST_MARKET, case=False, regex=True).sum())
    if n < MIN_HARVEST_SWIPES:
        return None
    return Harvest(swipes=n, remark=remark(HARVEST_REMARK, n))


def top_ups(food) -> TopUps | None:
    ups = food[food["is_top_up"]]
    if len(ups) < MIN_TOP_UPS:
        return None
    places = [
        TopUpPlace(name, n, float(ups.loc[ups["name"] == name, "amount"].mean()))
        for name, n in by_count_then_recent(ups, "name")[:TOP_UP_PLACES_SHOWN]
    ]
    return TopUps(count=len(ups), total=float(ups["amount"].sum()), places=places)

"""Pick dining personalities: everyone gets every one they match, and the first is their main one."""
from dataclasses import dataclass

from .highlights import DINING_DOLLARS


@dataclass
class Personality:
    name: str
    image: str  # file name (without .png) in static/styles/imgs/personalities
    blurb: str


CONNOISSEUR = Personality("Connoisseur", "connoisseur", "You've went to ALOT of dining vendors this semester. Honestly good for you! idk if i could do that like how do you go to so many places.")
FRANK_FANATIC = Personality("Frank Fanatic", "frankFanatic", "So you like frank huh.")
WORCESTER_WARRIOR = Personality("Worcester Warrior", "worcesterWarrior", "Worcester is basically your second dorm at this point. Respect.")
BERK_BEAST = Personality("Berk Beast", "berkBeast", "Hey Beast. I know you be tearing it up at Berk Parties")
HAMP_HEAD = Personality("Hamp Head", "hampHead", "A true Hamp loyalist. The vibes are just better there.")
BIG_SPENDER = Personality("Big Spender", "bigSpender", "You've spent ALOT of money this semester on blue wall. I really don't this the dining hall food is that bad")
CALORIE_CONSUMER = Personality("Calorie Consumer", "calorieConsumer", "So you really really like dining hall food. You've been there so many times you can practically live there.")
AVATAR = Personality("Avatar", "avatar", "Master of all four dining halls. You split your swipes between Worcester, Hamp, Berk and Frank so evenly you basically keep the balance of the dining world. You must also walk a shit ton holy god.")
QUICK_EATER = Personality("Quick Eater", "quickEater", "Either you're always rushing to class, or just hate finding a seat at the dining hall, you just love that grab n go. It is really good though tbh. Frank fil a chicken sanwiches are soooo good.")
EARLY_BIRD = Personality("Early Bird", "earlyBird", "You probrobly go to sleep at 10 every night. Good for you. I personally could never but whatever get that bag. Or you just get no sleep at all. Probably the latter.")
VAMPIRE = Personality("Vampire", "vampire", "Now you love the late night and waiting in line forever for some medicore food. Unless its the perogis. Or the sweet n sour chicken. Or honestly its not that bad but the lines make it bad. Why you up eating anyway go to sleep.")
BELLA_HADID = Personality("Bella Hadid", "bellaHadid", "You barely touched your meal plan this semester. Either you're living that model life or you've been surviving on iced coffee and vibes. Eat something bestie.")
GREEDY = Personality("Greedy", "greedy", "When one swipe isnt enough. Do you even measure your food on the scale?")
DOUBLE_TROUBLE = Personality("Double Trouble", "doubleTrouble", "Two swipes, one trip. Either you're feeding a friend or you're just that hungry.")
PERFECTLY_BALANCED = Personality("Perfectly Balanced", "perfectlyBalanced", "Perfectly balanced, as all things should be. You're on track to use basically every swipe/dining dollar on your plan.")
NIGHT_OWL_SNACKER = Personality("Night Owl Snacker", "nightOwlSnacker", "When the sun goes down the snacking begins. Those late night dining dollars add up.")
COFFEE_ADDICT = Personality("Coffee Addict", "coffeeAddict", "You're at the cafes more than some of the baristas. Maybe try water once.")
WEEKEND_GHOST = Personality("Weekend Ghost", "weekendGhost", "Monday to Friday you're everywhere, then the weekend hits and you vanish. Going home again?")
LUNCH_LORD = Personality("Lunch Lord", "lunchLord", "Lunch is your meal. Breakfast and dinner are just suggestions.")
AVERAGE_JOE = Personality("Average Joe", "averageJoe", "You're just an average umass dining enjoyer, nothing to be ashamed of. I didn't make that many personalties and its kinda hard to get some of them so my fault. But maybe you'll get a different personality next semester :p.")

# Every personality but Average Joe, in the order the rules check them: the first one someone
# matches is their main one.
PERSONALITIES = [CONNOISSEUR, WORCESTER_WARRIOR, BERK_BEAST, HAMP_HEAD, FRANK_FANATIC, GREEDY, BIG_SPENDER, CALORIE_CONSUMER,
                 AVATAR, QUICK_EATER, EARLY_BIRD, VAMPIRE, BELLA_HADID, DOUBLE_TROUBLE, PERFECTLY_BALANCED, NIGHT_OWL_SNACKER,
                 COFFEE_ADDICT, WEEKEND_GHOST, LUNCH_LORD]


# At least this share of all their meal swipes at one dining hall gets its personality, once
# there are enough swipes for it to mean something.
HALL_LOYALTY_SHARE = 0.9
HALL_LOYALTY_MIN_SWIPES = 20
HALL_PERSONALITIES = {"Worcester": WORCESTER_WARRIOR, "Berk": BERK_BEAST, "Hamp": HAMP_HEAD, "Frank": FRANK_FANATIC}

# Fewer meal swipes a week than this, on average, makes a Bella Hadid. Other plans can't be one,
# and neither can a plan too small to reach it (a 65-meal plan is about 4 a week).
BELLA_HADID_MEALS_PER_WEEK = {"YCMP": 5, "Unlimited": 10}


def bella_hadid(wrapped) -> bool:
    threshold = BELLA_HADID_MEALS_PER_WEEK.get(wrapped.meal_plan)
    if threshold is None or wrapped.meals_per_week is None:
        return False
    if wrapped.plan_meals_per_week is not None and wrapped.plan_meals_per_week < threshold:
        return False
    return wrapped.meals_per_week < threshold


# Each dining hall within this of an even 25% share of their dining hall swipes makes an Avatar.
AVATAR_SHARE_RANGE = 0.05
DINING_HALLS = ["Worcester", "Hamp", "Berk", "Frank"]


def avatar(total) -> bool:
    halls = sum(total[hall] for hall in DINING_HALLS)
    if halls < HALL_LOYALTY_MIN_SWIPES:
        return False
    even = 1 / len(DINING_HALLS)
    return all(abs(total[hall] / halls - even) <= AVATAR_SHARE_RANGE + 1e-9 for hall in DINING_HALLS)


# Topping up more than this share of their Harvest Market trips makes a Greedy, once there are
# enough trips for it to mean something.
GREEDY_TOP_UP_SHARE = 0.75
GREEDY_MIN_VISITS = 5


def greedy(wrapped) -> bool:
    if wrapped.harvest_visits < GREEDY_MIN_VISITS:
        return False
    return wrapped.harvest_top_ups > GREEDY_TOP_UP_SHARE * wrapped.harvest_visits


# At least this share of their meal swipes being double swipes makes a Double Trouble.
DOUBLE_TROUBLE_SHARE = 0.1


def double_trouble(wrapped) -> bool:
    fun = wrapped.highlights.fun
    if fun is None or wrapped.total_swipes < HALL_LOYALTY_MIN_SWIPES:
        return False
    return fun.double_swipes >= DOUBLE_TROUBLE_SHARE * wrapped.total_swipes - 1e-9


# A plan on pace to end the semester with no more than this share of it left, without running
# out first, makes a Perfectly Balanced.
PERFECTLY_BALANCED_LEFT = 0.05


def balanced_plan(wrapped):
    """The PlanPace Perfectly Balanced looks at: dining dollars on an unlimited plan (the swipes
    never run out), otherwise their meal swipes."""
    if wrapped.meal_plan == "Unlimited":
        return next((plan for plan in wrapped.highlights.plans if plan.label == DINING_DOLLARS), None)
    return next((plan for plan in wrapped.highlights.plans if plan.is_meals), None)


def perfectly_balanced(wrapped) -> bool:
    plan = balanced_plan(wrapped)
    if plan is None or plan.runs_out is not None:
        return False
    return plan.left_at_end <= PERFECTLY_BALANCED_LEFT * (plan.used + plan.left)


# A week, on average.
NIGHT_OWL_SNACKS_PER_WEEK = 1
COFFEE_TRIPS_PER_WEEK = 4

# Fewer than this share of their visits on Saturday or Sunday makes a Weekend Ghost.
WEEKEND_GHOST_SHARE = 0.05
WEEKEND_GHOST_MIN_VISITS = 30


def weekend_visits(wrapped) -> tuple[int, int]:
    """(visits on Saturday or Sunday, all visits)."""
    clock = wrapped.highlights.clock
    if clock is None:
        return 0, 0
    by_day = {day: sum(hours.values()) for day, hours in clock.grid.items()}
    return by_day["Saturday"] + by_day["Sunday"], sum(by_day.values())


def weekend_ghost(wrapped) -> bool:
    weekend, visits = weekend_visits(wrapped)
    return visits >= WEEKEND_GHOST_MIN_VISITS and weekend < WEEKEND_GHOST_SHARE * visits


# At least this share of their meal swipes at lunch makes a Lunch Lord.
LUNCH_LORD_SHARE = 0.7


def plural(n, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def matches(wrapped):
    """(personality, why they got it) for every personality they match, in PERSONALITIES order."""
    swipes = wrapped.swipes.fillna(0)
    total = swipes.loc["Total"]

    if wrapped.places_tried > 15:
        yield CONNOISSEUR, f"You ate at {wrapped.places_tried} different food places."
    for hall, personality in HALL_PERSONALITIES.items():
        if wrapped.total_swipes >= HALL_LOYALTY_MIN_SWIPES and total[hall] >= HALL_LOYALTY_SHARE * wrapped.total_swipes:
            yield personality, f"{total[hall] / wrapped.total_swipes:.0%} of your meal swipes were at {hall}."
    if greedy(wrapped):
        yield GREEDY, f"You topped up {wrapped.harvest_top_ups} of your {wrapped.harvest_visits} Harvest Market visits."
    if wrapped.total_spent > 250:
        yield BIG_SPENDER, f"You spent ${wrapped.total_spent:,.2f} in dining dollars on food."
    if wrapped.total_swipes > 300:
        yield CALORIE_CONSUMER, f"You used {wrapped.total_swipes} meal swipes."
    if avatar(total):
        halls = sum(total[hall] for hall in DINING_HALLS)
        split = ", ".join(f"{hall} {total[hall] / halls:.0%}" for hall in DINING_HALLS)
        yield AVATAR, f"Your dining hall swipes were split almost evenly: {split}."
    grab_n_go = int(swipes.loc["GrabNGo", "Worcester"] + swipes.loc["GrabNGo", "Frank"])
    if grab_n_go > 100:
        yield QUICK_EATER, f"You got {grab_n_go} meals from Grab 'n Go."
    breakfasts = int(swipes.loc["Breakfast"].sum())
    if breakfasts > 100:
        yield EARLY_BIRD, f"You swiped in for breakfast {breakfasts} times."
    late_nights = int(swipes.loc["Late_Night", "Worcester"] + swipes.loc["Late_Night", "Berk"])
    if late_nights > 75:
        yield VAMPIRE, f"You swiped in for late night {late_nights} times."
    if bella_hadid(wrapped):
        yield BELLA_HADID, f"You averaged {wrapped.meals_per_week:.1f} meal swipes a week."
    if double_trouble(wrapped):
        doubles = wrapped.highlights.fun.double_swipes
        yield DOUBLE_TROUBLE, f"You double swiped {plural(doubles, 'time')} in {wrapped.total_swipes} meal swipes."
    if perfectly_balanced(wrapped):
        plan = balanced_plan(wrapped)
        what = "meal swipes" if plan.is_meals else "dining dollars"
        left = (plural(round(plan.left_at_end), "meal swipe") if plan.is_meals
                else f"${plan.left_at_end:.2f} in dining dollars")
        yield PERFECTLY_BALANCED, (f"At this pace your {what} last right up to the end of the semester." if plan.left_at_end <= 0
                                   else f"At this pace you'll end the semester with just {left} left.")
    if (wrapped.late_snacks_per_week or 0) >= NIGHT_OWL_SNACKS_PER_WEEK:
        yield NIGHT_OWL_SNACKER, f"You bought food between 9pm and 4am about {wrapped.late_snacks_per_week:.1f} times a week."
    if (wrapped.coffee_per_week or 0) >= COFFEE_TRIPS_PER_WEEK:
        yield COFFEE_ADDICT, f"You made about {wrapped.coffee_per_week:.1f} coffee runs a week."
    if weekend_ghost(wrapped):
        weekend, visits = weekend_visits(wrapped)
        yield WEEKEND_GHOST, (f"None of your {visits} visits were on a weekend." if weekend == 0 else
                              f"Only {weekend} of your {visits} visits were on a weekend.")
    lunches = swipes.loc["Lunch"].sum()
    if wrapped.total_swipes >= HALL_LOYALTY_MIN_SWIPES and lunches >= LUNCH_LORD_SHARE * wrapped.total_swipes - 1e-9:
        yield LUNCH_LORD, f"{lunches / wrapped.total_swipes:.0%} of your meal swipes were at lunch."


def pick_personalities(wrapped) -> tuple[list[Personality], dict[str, str]]:
    """Every personality they match, main one first, and why they got each one (by name).
    Average Joe, with no reason, only if there are none."""
    found = list(matches(wrapped))
    if not found:
        return [AVERAGE_JOE], {}
    return [personality for personality, _ in found], {personality.name: why for personality, why in found}


def wheel_cards(personalities) -> list[Personality]:
    """The cards on the personality wheel: every personality, and Average Joe only for people who got it."""
    return PERSONALITIES + [AVERAGE_JOE] if AVERAGE_JOE in personalities else PERSONALITIES

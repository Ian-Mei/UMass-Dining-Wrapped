"""Pick a dining personality. The first rule that matches wins."""
from dataclasses import dataclass


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
PERFECTLY_BALANCED = Personality("Perfectly Balanced", "perfectlyBalanced", "Perfectly balanced, as all things should be. You're on track to use basically every swipe on your plan.")
NIGHT_OWL_SNACKER = Personality("Night Owl Snacker", "nightOwlSnacker", "When the sun goes down the snacking begins. Those late night dining dollars add up.")
COFFEE_ADDICT = Personality("Coffee Addict", "coffeeAddict", "You're at the cafes more than some of the baristas. Maybe try water once.")
WEEKEND_GHOST = Personality("Weekend Ghost", "weekendGhost", "Monday to Friday you're everywhere, then the weekend hits and you vanish. Going home again?")
LUNCH_LORD = Personality("Lunch Lord", "lunchLord", "Lunch is your meal. Breakfast and dinner are just suggestions.")
AVERAGE_JOE = Personality("Average Joe", "averageJoe", "You're just an average umass dining enjoyer, nothing to be ashamed of. I didn't make that many personalties and its kinda hard to get some of them so my fault. But maybe you'll get a different personality next semester :p.")


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


# A meal plan on pace to end the semester with no more than this share of it left, without
# running out first, makes a Perfectly Balanced.
PERFECTLY_BALANCED_LEFT = 0.05


def perfectly_balanced(wrapped) -> bool:
    meals = next((plan for plan in wrapped.highlights.plans if plan.is_meals), None)
    if meals is None or meals.runs_out is not None:
        return False
    return meals.left_at_end <= PERFECTLY_BALANCED_LEFT * (meals.used + meals.left)


# A week, on average.
NIGHT_OWL_SNACKS_PER_WEEK = 1
COFFEE_TRIPS_PER_WEEK = 4

# Fewer than this share of their visits on Saturday or Sunday makes a Weekend Ghost.
WEEKEND_GHOST_SHARE = 0.05
WEEKEND_GHOST_MIN_VISITS = 30


def weekend_ghost(wrapped) -> bool:
    clock = wrapped.highlights.clock
    if clock is None:
        return False
    by_day = {day: sum(hours.values()) for day, hours in clock.grid.items()}
    visits = sum(by_day.values())
    return visits >= WEEKEND_GHOST_MIN_VISITS and by_day["Saturday"] + by_day["Sunday"] < WEEKEND_GHOST_SHARE * visits


# At least this share of their meal swipes at lunch makes a Lunch Lord.
LUNCH_LORD_SHARE = 0.7


def pick_personality(wrapped) -> Personality:
    swipes = wrapped.swipes.fillna(0)
    total = swipes.loc["Total"]

    if wrapped.places_tried > 15:
        return CONNOISSEUR
    for hall, personality in HALL_PERSONALITIES.items():
        if wrapped.total_swipes >= HALL_LOYALTY_MIN_SWIPES and total[hall] >= HALL_LOYALTY_SHARE * wrapped.total_swipes:
            return personality
    if greedy(wrapped):
        return GREEDY
    if wrapped.total_spent > 250:
        return BIG_SPENDER
    if wrapped.total_swipes > 300:
        return CALORIE_CONSUMER
    if avatar(total):
        return AVATAR
    if swipes.loc["GrabNGo", "Worcester"] + swipes.loc["GrabNGo", "Frank"] > 100:
        return QUICK_EATER
    if swipes.loc["Breakfast"].sum() > 100:
        return EARLY_BIRD
    if swipes.loc["Late_Night", "Worcester"] + swipes.loc["Late_Night", "Berk"] > 75:
        return VAMPIRE
    if bella_hadid(wrapped):
        return BELLA_HADID
    if double_trouble(wrapped):
        return DOUBLE_TROUBLE
    if perfectly_balanced(wrapped):
        return PERFECTLY_BALANCED
    if (wrapped.late_snacks_per_week or 0) >= NIGHT_OWL_SNACKS_PER_WEEK:
        return NIGHT_OWL_SNACKER
    if (wrapped.coffee_per_week or 0) >= COFFEE_TRIPS_PER_WEEK:
        return COFFEE_ADDICT
    if weekend_ghost(wrapped):
        return WEEKEND_GHOST
    if wrapped.total_swipes >= HALL_LOYALTY_MIN_SWIPES and swipes.loc["Lunch"].sum() >= LUNCH_LORD_SHARE * wrapped.total_swipes - 1e-9:
        return LUNCH_LORD
    return AVERAGE_JOE

"""Pick a dining personality. The first rule that matches wins."""
from dataclasses import dataclass


@dataclass
class Personality:
    name: str
    image: str  # file name (without .png) in static/styles/imgs
    blurb: str


CONNOISSEUR = Personality("Connoisseur", "connoisseur", "You've went to ALOT of dining vendors this semester. Honestly good for you! idk if i could do that like how do you go to so many places.")
FRANK_ENJOYER = Personality("Frank Enjoyer", "frankEnjoyer", "So you like frank huh.")
BIG_SPENDER = Personality("Big Spender", "bigSpender", "You've spent ALOT of money this semester on blue wall. I really don't this the dining hall food is that bad")
CALORIE_CONSUMER = Personality("Calorie Consumer", "calorieConsumer", "So you really really like dining hall food. You've been there so many times you can practically live there.")
VOYAGER = Personality("Voyager", "voyager", "You love every dining hall huh. You're probably a little indecisive, or just want to share your love to every dining hall. You must also walk a shit ton holy god.")
QUICK_EATER = Personality("Quick Eater", "quickEater", "Either you're always rushing to class, or just hate finding a seat at the dining hall, you just love that grab n go. It is really good though tbh. Frank fil a chicken sanwiches are soooo good.")
EARLY_BIRD = Personality("Early Bird", "earlyBird", "You probrobly go to sleep at 10 every night. Good for you. I personally could never but whatever get that bag. Or you just get no sleep at all. Probably the latter.")
VAMPIRE = Personality("Vampire", "vampire", "Now you love the late night and waiting in line forever for some medicore food. Unless its the perogis. Or the sweet n sour chicken. Or honestly its not that bad but the lines make it bad. Why you up eating anyway go to sleep.")
AVERAGE_JOE = Personality("Average Joe", "averageJoe", "You're just an average umass dining enjoyer, nothing to be ashamed of. I didn't make that many personalties and its kinda hard to get some of them so my fault. But maybe you'll get a different personality next semester :p.")


def pick_personality(wrapped) -> Personality:
    swipes = wrapped.swipes.fillna(0)
    total = swipes.loc["Total"]

    if len(wrapped.vendors) > 15:
        return CONNOISSEUR
    if total["Frank"] > 125:
        return FRANK_ENJOYER
    if wrapped.total_spent > 250:
        return BIG_SPENDER
    if wrapped.total_swipes > 300:
        return CALORIE_CONSUMER
    if all(total[hall] > 40 for hall in ["Worcester", "Hamp", "Berk", "Frank"]):
        return VOYAGER
    if swipes.loc["GrabNGo", "Worcester"] + swipes.loc["GrabNGo", "Frank"] > 100:
        return QUICK_EATER
    if swipes.loc["Breakfast"].sum() > 100:
        return EARLY_BIRD
    if swipes.loc["Late_Night", "Worcester"] + swipes.loc["Late_Night", "Berk"] > 75:
        return VAMPIRE
    return AVERAGE_JOE

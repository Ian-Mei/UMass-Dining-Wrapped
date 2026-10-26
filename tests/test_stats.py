from datetime import date, datetime, timedelta

import pytest

from wrapped import ParseError, build_wrapped
from wrapped.personality import (AVATAR, AVERAGE_JOE, BELLA_HADID, BERK_BEAST, BIG_SPENDER, COFFEE_ADDICT, CONNOISSEUR,
                                 DOUBLE_TROUBLE, FRANK_FANATIC, GREEDY, HAMP_HEAD, LUNCH_LORD, NIGHT_OWL_SNACKER,
                                 PERFECTLY_BALANCED, QUICK_EATER, WEEKEND_GHOST, WORCESTER_WARRIOR)
from wrapped.transactions import account_history
from wrapped.transactions import clean

from .conftest import charge, swipe


def wrapped_from(rows):
    return build_wrapped(clean(rows))


def test_dining_hall_meal_periods():
    w = wrapped_from([
        swipe("HampDC2", "March 4, 2024, 8:00AM"),
        swipe("HampDC3", "March 4, 2024, 12:00PM"),
        swipe("HampDC3", "March 5, 2024, 12:00PM"),
        swipe("HampDC4", "March 4, 2024, 6:00PM"),
        swipe("WorcDC1", "March 4, 2024, 1:00PM"),   # Grab 'n Go register
        swipe("WorcDC2", "March 4, 2024, 10:00PM"),  # late night
        swipe("WorcDC2", "March 5, 2024, 12:30AM"),  # still late night, not breakfast
        swipe("BerkDC1", "March 4, 2024, 11:00PM"),  # register 1 at Berk is not Grab 'n Go
    ])

    assert w.swipes["Hamp"].to_dict() == {
        "Breakfast": 1, "Lunch": 2, "Dinner": 1, "Late_Night": None, "GrabNGo": None, "Total": 4,
    }
    assert w.swipes["Worcester"].to_dict() == {
        "Breakfast": 0, "Lunch": 0, "Dinner": 0, "Late_Night": 2, "GrabNGo": 1, "Total": 3,
    }
    assert w.swipes.loc["Late_Night", "Berk"] == 1
    assert w.swipes.loc["GrabNGo", "Frank"] == 0
    assert w.hall_ranking == [("Hamp", 4), ("Worcester", 3), ("Berk", 1)]
    assert w.favorite_hall == "Hamp"
    assert w.total_swipes == 8


def test_dining_halls_under_2026_terminal_names():
    # By Fall 2026 GET names terminals "CPOS Worcester DC" / "CPOS Worcester GG" (Grab 'n Go).
    w = wrapped_from([
        swipe("CPOS Worcester DC", "09/02/26 12:00:00 PM"),
        swipe("CPOS Worcester DC", "09/02/26 10:00:00 PM"),
        swipe("CPOS Worcester GG", "09/03/26 12:00:00 PM"),
        swipe("CPOS Hampshire DC", "09/03/26 08:00:00 AM"),
        swipe("CPOS Berkshire DC", "09/03/26 06:00:00 PM"),
        swipe("CPOS Franklin GG", "09/04/26 01:00:00 PM"),
    ])
    assert w.swipes["Worcester"].to_dict() == {
        "Breakfast": 0, "Lunch": 1, "Dinner": 0, "Late_Night": 1, "GrabNGo": 1, "Total": 3,
    }
    assert w.swipes.loc["GrabNGo", "Frank"] == 1
    assert w.hall_ranking == [("Worcester", 3), ("Hamp", 1), ("Berk", 1), ("Frank", 1)]
    assert w.total_swipes == 6


def test_swipes_outside_dining_halls_get_their_own_column():
    w = wrapped_from([swipe("Roots Cafe 1", "March 4, 2024, 9:00AM")])
    assert w.swipes.loc["Total", "Roots Cafe"] == 1
    assert w.swipes.loc["Breakfast", "Roots Cafe"] == 1
    assert w.vendors.empty
    assert w.total_swipes == 1


def test_vendor_spending():
    w = wrapped_from([
        charge("Wasabi 1", "March 4, 2024, 12:00PM", 10.00),
        charge("Wasabi 2", "March 5, 2024, 10:30PM", 10.50),  # late night counts as dinner
        charge("The Grill 1", "March 4, 2024, 9:00AM", 12.00),
    ])
    assert w.vendors.index.tolist() == ["Wasabi", "The Grill"]
    assert w.vendors.loc["Wasabi"].to_dict() == {"breakfast": 0, "lunch": 1, "dinner": 1, "visits": 2, "spent": 20.5}
    assert w.total_spent == pytest.approx(32.5)


def test_without_a_meal_plan():
    w = wrapped_from([
        charge("The Grill 2", "12/13/23 06:49:03 PM", 19.50),
        ["Student Debit Plan", "12/13/23 01:41:00 PM", "X - OAK DRYER 10", "-$1.40", "$5.80"],
        ["Student Debit Plan", "12/13/23 12:52:00 PM", "X - OAK WASHER 08", "-$1.40", "$7.20"],
        ["Student Debit Plan", "12/14/23 12:52:00 PM", "X - OAK WASHER 08", "-$1.40", "$5.80"],
    ])
    assert w.hall_ranking == []
    assert w.favorite_hall is None
    assert w.total_swipes == 0
    assert w.total_spent == pytest.approx(19.5)
    assert w.laundry.washes == 2
    assert w.laundry.dries == 1
    assert w.laundry.spent == pytest.approx(4.2)
    assert w.laundry.favorite_machine == "OAK WASHER 08"
    assert w.personality == AVERAGE_JOE
    assert w.semester == "Fall 2023"
    assert w.semester_short == "Fall 23"


def test_personality_rules():
    big_spender = [charge("Wasabi 1", f"March {d}, 2024, 12:00PM", 20.00) for d in range(1, 15)]
    assert wrapped_from(big_spender).personality == BIG_SPENDER

    # Split between Frank's and Worcester's, so it isn't 90% at one hall.
    grab_n_go = [swipe("FrankDC1" if d % 2 else "CPOS Worcester GG", f"March {d % 28 + 1}, 2024, 1:{d % 60:02d}PM") for d in range(101)]
    assert wrapped_from(grab_n_go).personality == QUICK_EATER


@pytest.mark.parametrize("hall, expected", [
    ("Worcester DC", WORCESTER_WARRIOR), ("Berkshire DC", BERK_BEAST), ("Hampshire DC", HAMP_HEAD), ("Franklin DC", FRANK_FANATIC),
])
def test_hall_loyalty_personalities(hall, expected):
    first = datetime(2026, 9, 7, 12)
    at = lambda place, d: swipe(f"CPOS {place}", (first + timedelta(days=d)).strftime("%m/%d/%y %I:%M:%S %p"))
    other = "Tamales" if hall != "Worcester DC" else "Franklin DC"
    nine_in_ten = [at(hall, d) for d in range(27)] + [at(other, d + 27) for d in range(3)]
    assert wrapped_from(nine_in_ten).personality == expected
    eight_in_ten = [at(hall, d) for d in range(24)] + [at(other, d + 24) for d in range(6)]
    assert wrapped_from(eight_in_ten).personality != expected
    assert wrapped_from(nine_in_ten[:19]).personality != expected  # too few swipes to tell


@pytest.mark.parametrize("account, per_week, expected", [
    ("T YCMP Commuter 155", 4, BELLA_HADID),
    ("T YCMP Commuter 155", 5, AVERAGE_JOE),
    ("E Unlimited 250", 9, BELLA_HADID),
    ("E Unlimited 250", 10, AVERAGE_JOE),
    ("C Basic Plan", 2, AVERAGE_JOE),  # only YCMP and unlimited plans
    ("K YCMP Gold", 4, BELLA_HADID),   # no meal count in the name, so it isn't skipped
    ("G YCMP Cmmtr 65", 4, AVERAGE_JOE),  # 65 meals is only about 4 a week
])
def test_bella_hadid_eats_less_than_their_plan_expects(account, per_week, expected):
    first = datetime(2026, 9, 7, 8)  # a Monday
    # Spread over the whole week, weekend too, so it isn't a Weekend Ghost.
    rows = [swipe("CPOS Hampshire DC" if w % 2 else "CPOS Berkshire DC",  # not 90% at one hall
                  (first + timedelta(weeks=w, days=d * 7 // per_week, hours=d % 2 * 6)).strftime("%m/%d/%y %I:%M:%S %p"), account)
            for w in range(10) for d in range(per_week)]
    w = build_wrapped(clean(rows), today=date(2026, 11, 16))  # 10 weeks after the first swipe
    assert w.personality == expected


def test_no_bella_hadid_in_the_first_two_weeks():
    rows = [swipe("CPOS Hampshire DC", "09/07/26 12:00:00 PM", "E Unlimited 250")]
    assert build_wrapped(clean(rows), today=date(2026, 9, 18)).personality == AVERAGE_JOE


def test_connoisseur_counts_every_food_place_swiped_or_paid_at():
    rows = [swipe("CPOS Worcester DC", "10/05/26 12:00:00 PM"), swipe("CPOS Worcester GG", "10/05/26 06:00:00 PM"),  # one place
            swipe("CPOS Hampshire DC", "10/06/26 12:00:00 PM"), charge("CPOS Franklin DC", "10/06/26 06:00:00 PM", 12),
            swipe("CPOS Tamales", "10/07/26 12:00:00 PM", account="T YCMP Commuter 155")]
    rows += [charge(f"CPOS Cafe {chr(65 + n)}", f"10/{8 + n:02d}/26 09:00:00 AM", 4) for n in range(12)]
    assert wrapped_from(rows).places_tried == 16
    assert wrapped_from(rows).personality == CONNOISSEUR
    assert wrapped_from(rows[:-1]).personality != CONNOISSEUR  # 15 isn't more than 15


def hall_swipes(counts):
    """{hall location: n} -> n swipes there, one a day from Sep 7 2026."""
    first, rows = datetime(2026, 9, 7, 12), []
    for hall, n in counts.items():
        rows += [swipe(f"CPOS {hall}", (first + timedelta(days=len(rows))).strftime("%m/%d/%y %I:%M:%S %p")) for _ in range(n)]
    return rows


def test_avatar_splits_swipes_evenly_between_the_dining_halls():
    # 30% / 25% / 25% / 20% of 40 is still even enough; 32.5% isn't.
    assert wrapped_from(hall_swipes({"Worcester DC": 12, "Hampshire DC": 10, "Berkshire DC": 10, "Franklin DC": 8})).personality == AVATAR
    assert wrapped_from(hall_swipes({"Worcester DC": 13, "Hampshire DC": 10, "Berkshire DC": 10, "Franklin DC": 7})).personality != AVATAR
    assert wrapped_from(hall_swipes({"Worcester DC": 4, "Hampshire DC": 4, "Berkshire DC": 4, "Franklin DC": 4})).personality != AVATAR  # too few


def harvest_trips(topped_up, plain):
    rows = []
    for d in range(1, topped_up + plain + 1):
        when = f"10/{d:02d}/26 12:00:"
        rows.append(swipe("CPOS Harvest Market", when + "00 PM", account="T YCMP Commuter 155"))
        if d <= topped_up:
            rows.append(charge("CPOS Harvest Market", when + "08 PM", 4.50))
    return rows


def test_greedy_tops_up_most_harvest_market_swipes():
    w = wrapped_from(harvest_trips(topped_up=4, plain=1))
    assert (w.harvest_visits, w.harvest_top_ups) == (5, 4)
    assert w.personality == GREEDY
    assert wrapped_from(harvest_trips(topped_up=3, plain=1)).personality != GREEDY  # too few trips
    assert wrapped_from(harvest_trips(topped_up=6, plain=2)).personality != GREEDY  # 75% isn't more than 75%


def test_a_double_swipe_at_harvest_market_is_one_visit():
    rows = harvest_trips(topped_up=4, plain=1)
    rows += [swipe("CPOS Harvest Market", f"10/{d:02d}/26 12:00:04 PM", account="T YCMP Commuter 155") for d in (1, 2)]
    w = wrapped_from(rows)
    assert (w.harvest_visits, w.harvest_top_ups) == (5, 4)
    assert w.personality == GREEDY


FIRST_MONDAY = datetime(2026, 9, 7)
NO_PLAN = "C Basic Plan"  # so a small test history isn't a Bella Hadid


def stamp(when):
    return when.strftime("%m/%d/%y %I:%M:%S %p")


def meals(days, hour=12, minute=0):
    """One swipe on each of these days after Sep 7 2026, alternating Worcester and Hamp."""
    return [swipe("CPOS Worcester DC" if d % 2 else "CPOS Hampshire DC",
                  stamp(FIRST_MONDAY + timedelta(days=d, hours=hour, minutes=minute)), NO_PLAN) for d in days]


def test_double_trouble_double_swipes_a_tenth_of_the_time():
    rows = meals(range(20), hour=18)
    seconds_later = lambda d: [swipe("CPOS Worcester DC" if d % 2 else "CPOS Hampshire DC",
                                     stamp(FIRST_MONDAY + timedelta(days=d, hours=18, seconds=30)), NO_PLAN)]
    assert wrapped_from(rows + seconds_later(0) + seconds_later(1) + seconds_later(2)).personality == DOUBLE_TROUBLE  # 3 of 23
    assert wrapped_from(rows + seconds_later(0) + seconds_later(1)).personality != DOUBLE_TROUBLE  # 2 of 22


@pytest.mark.parametrize("left, expected", [(17, PERFECTLY_BALANCED), (20, AVERAGE_JOE), (15, AVERAGE_JOE)])
def test_perfectly_balanced_ends_the_semester_with_almost_no_swipes_left(left, expected):
    # 20 swipes in 60 days, so 16 more by Dec 18: 17 left ends with 1 (under 5%), 20 with 4, and
    # 15 runs out.
    account = f"T YCMP Commuter {20 + left}"
    rows = [[account, stamp(FIRST_MONDAY + timedelta(days=3 * n - 6, hours=18)),
             "CPOS Worcester DC" if n % 2 else "CPOS Hampshire DC", "-1", str(20 + left - n - 1)] for n in range(20)]
    w = build_wrapped(clean(rows), today=date(2026, 10, 31), history=account_history(rows))
    assert w.personality == expected


def test_weekend_ghost_barely_eats_on_campus_on_weekends():
    weekdays = [d for d in range(42) if d % 7 < 5]  # Sep 7 is a Monday
    assert wrapped_from(meals(weekdays, hour=18)).personality == WEEKEND_GHOST
    assert wrapped_from(meals(weekdays + [5, 6], hour=18)).personality != WEEKEND_GHOST  # 2 of 32 is over 5%
    assert wrapped_from(meals(weekdays[:29], hour=18)).personality != WEEKEND_GHOST  # too few visits to tell


def test_coffee_addict_goes_for_coffee_four_times_a_week():
    coffee = lambda days: [charge("CPOS Peets Coffee", stamp(FIRST_MONDAY + timedelta(days=d, hours=9)), 4.50) for d in days]
    assert wrapped_from(coffee(range(0, 15, 2))).personality == COFFEE_ADDICT  # 8 in 2 weeks
    assert wrapped_from(coffee([0, 2, 4, 6, 8, 10, 14])).personality != COFFEE_ADDICT  # 7 in 2 weeks
    assert wrapped_from(coffee(range(13))).personality != COFFEE_ADDICT  # a lot, but in under 2 weeks


def test_night_owl_snacker_buys_food_late_every_week():
    snacks = lambda hour: [charge("CPOS Wasabi", stamp(FIRST_MONDAY + timedelta(days=d, hours=hour)), 6) for d in (0, 7, 14)]
    assert wrapped_from(snacks(23)).personality == NIGHT_OWL_SNACKER
    assert wrapped_from(snacks(25)).personality == NIGHT_OWL_SNACKER  # 1am is still that night
    assert wrapped_from(snacks(20)).personality != NIGHT_OWL_SNACKER


def test_lunch_lord_swipes_mostly_at_lunch():
    assert wrapped_from(meals(range(21)) + meals(range(21, 30), hour=18)).personality == LUNCH_LORD  # 70%
    assert wrapped_from(meals(range(20)) + meals(range(20, 30), hour=18)).personality != LUNCH_LORD  # 67%
    assert wrapped_from(meals(range(19))).personality != LUNCH_LORD  # too few swipes to tell


def test_no_purchases_is_an_error():
    with pytest.raises(ParseError):
        wrapped_from([])


def test_vendor_and_swipe_names_are_cleaned_up():
    w = wrapped_from([
        charge("CPOS ISB CafÃ©", "10/05/26 12:00:00 PM", 4.75),
        swipe("CPOS Roots Cafe", "10/06/26 09:00:00 AM"),
    ])
    assert w.vendors.index.tolist() == ["ISB Café"]
    assert w.swipes.loc["Total", "Roots Cafe"] == 1


def test_top_ups_leave_top_spots_but_count_toward_total_spent():
    w = wrapped_from([
        swipe("CPOS Harvest Market", "10/05/26 12:00:00 PM", account="T YCMP Commuter 155"),
        charge("CPOS Harvest Market", "10/05/26 12:00:08 PM", 4.50),  # topped up the swipe
        charge("CPOS Harvest Market", "10/06/26 03:00:00 PM", 6.00),  # bought on its own
    ])
    assert w.vendors.loc["Harvest Market", "visits"] == 1
    assert w.vendors.loc["Harvest Market", "spent"] == pytest.approx(6.00)
    assert w.total_spent == pytest.approx(10.50)


def test_a_swipe_with_an_unreadable_amount_still_counts_once():
    w = wrapped_from([["M Unlimited DC", "10/05/26 12:00:00 PM", "CPOS Worcester DC", "-", "500"]])
    assert w.total_swipes == 1


def test_unreadable_amounts_are_one_swipe_or_no_dollars():
    tx = clean([["M Unlimited DC", "10/05/26 12:00:00 PM", "CPOS Worcester DC", "-", "500"],
                ["UMass Dining Dollars", "10/05/26 01:00:00 PM", "CPOS Tamales", "-$", "$88.00"]])
    assert list(tx["amount"]) == [1, 0]


def test_dining_dollars_paid_at_a_hall_are_not_swipes():
    w = wrapped_from([
        swipe("CPOS Hampshire DC", "10/05/26 12:00:00 PM"),
        ["UMass Dining Dollars", "10/06/26 06:00:00 PM", "CPOS Hampshire DC", "-$12.00", "$88.00"],
    ])
    assert w.swipes.loc["Total", "Hamp"] == 1
    assert w.total_swipes == 1
    assert w.total_spent == pytest.approx(12)

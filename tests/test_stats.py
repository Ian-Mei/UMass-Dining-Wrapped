import pytest

from wrapped import ParseError, build_wrapped
from wrapped.personality import AVERAGE_JOE, BIG_SPENDER, QUICK_EATER
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

    grab_n_go = [swipe("FrankDC1", f"March {d % 28 + 1}, 2024, 1:{d % 60:02d}PM") for d in range(101)]
    assert wrapped_from(grab_n_go).personality == QUICK_EATER


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

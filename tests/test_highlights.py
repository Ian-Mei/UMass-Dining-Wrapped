from datetime import date, time

import pytest

from wrapped import build_wrapped
from wrapped.highlights import blue_wall_name, display_name
from wrapped.transactions import clean


def highlights(rows, today=None):
    tx = clean(rows)
    # By default, run it the day of the last purchase.
    return build_wrapped(tx, today=today or tx["timestamp"].max().date()).highlights


def meal(location, when, account="M Unlimited DC", balance="500"):
    return [account, when, location, "-1", balance]


def dollars(location, when, amount, balance, account="UMass Dining Dollars"):
    return [account, when, location, f"-${amount:.2f}", f"${balance:.2f}"]


@pytest.mark.parametrize("place, hall, grab, expected", [
    ("CPOS Worcester DC", "Worcester", False, "Worcester"),
    ("CPOS Worcester GG", "Worcester", True, "Worcester Grab 'n Go"),
    ("WorcDC", "Worcester", False, "Worcester"),
    ("CPOS Harvest Market", None, False, "Harvest Market"),
    ("CPOS ISB CafÃ©", None, False, "ISB Café"),
    ("The Grill", None, False, "The Grill"),
])
def test_display_name(place, hall, grab, expected):
    assert display_name(place, hall, grab) == expected


def test_dining_dollars_running_out():
    # $10 every other day from Sep 1 to Oct 1: $160 used, $40 left, ~$5.33 a day.
    rows = [dollars("CPOS Wasabi", f"09/{d:02d}/26 12:00:00 PM", 10, 200 - 10 * (i + 1))
            for i, d in enumerate(range(1, 31, 2))]
    rows.append(dollars("CPOS Wasabi", "10/01/26 12:00:00 PM", 10, 40))
    [plan] = highlights(rows).plans
    assert plan.label == "Dining Dollars"
    assert plan.is_meals is False
    assert plan.used == pytest.approx(160)
    assert plan.left == pytest.approx(40)
    assert plan.runs_out == date(2026, 10, 8)
    assert plan.left_at_end == 0


def test_quiet_days_up_to_today_slow_the_pace():
    # Same $160 used and $40 left as above, but run on Oct 11 after 10 days without buying:
    # $160 over 40 days is $4 a day, so $40 lasts until Oct 21.
    rows = [dollars("CPOS Wasabi", f"09/{d:02d}/26 12:00:00 PM", 10, 200 - 10 * (i + 1))
            for i, d in enumerate(range(1, 31, 2))]
    rows.append(dollars("CPOS Wasabi", "10/01/26 12:00:00 PM", 10, 40))
    [plan] = highlights(rows, today=date(2026, 10, 11)).plans
    assert plan.per_week == pytest.approx(4 * 7)
    assert plan.runs_out == date(2026, 10, 21)


def test_running_it_after_the_semester_reports_what_was_left():
    rows = [dollars("CPOS Wasabi", f"12/{d:02d}/26 12:00:00 PM", 10, 100 - 10 * d) for d in range(1, 7)]
    [plan] = highlights(rows, today=date(2027, 1, 10)).plans  # winter break, weeks after the last purchase
    assert plan.runs_out is None
    assert plan.left_at_end == pytest.approx(40)


def test_meal_plan_with_swipes_to_spare():
    # 21 of 155 swipes used in 30 days; at 0.7 a day another ~55 get used by Dec 18.
    rows = [meal("CPOS Worcester DC", f"09/{d:02d}/26 12:00:00 PM", "T YCMP Commuter 155", str(155 - i - 1))
            for i, d in enumerate(range(1, 21))]
    rows.append(meal("CPOS Worcester DC", "10/01/26 06:00:00 PM", "T YCMP Commuter 155", "134"))
    [plan] = highlights(rows).plans
    assert plan.label == "Meal Swipes"
    assert plan.left == 134
    assert plan.runs_out is None
    assert plan.left_at_end == 79
    assert plan.per_week == pytest.approx(21 / 30 * 7)


def test_plans_skip_unlimited_and_flat_balances():
    rows = [meal("CPOS Worcester DC", f"09/{d:02d}/26 12:00:00 PM", "M Unlimited DC", str(600 - d)) for d in range(1, 10)]
    rows += [meal("CPOS Hampshire DC", f"09/{d:02d}/26 01:00:00 PM", "Free Friday DC", "0") for d in range(1, 10)]
    rows += [dollars("CPOS Wasabi", f"09/0{d}/26 02:00:00 PM", 5, 100 - 5 * d) for d in range(1, 4)]  # too few
    # A training account that stopped being used weeks before the latest purchase.
    rows += [meal("CPOS Hampshire DC", f"09/0{d}/26 06:00:00 PM", "EA RA&PM Training", str(10 - d)) for d in range(1, 7)]
    rows.append(meal("CPOS Worcester DC", "10/19/26 12:00:00 PM"))
    assert highlights(rows).plans == []


def test_plan_after_the_semester_reports_what_was_left():
    rows = [dollars("CPOS Wasabi", f"12/{d:02d}/26 12:00:00 PM", 10, 100 - 10 * d) for d in range(1, 7)]
    rows.append(dollars("CPOS Wasabi", "12/19/26 12:00:00 PM", 1, 39))
    [plan] = highlights(rows).plans
    assert plan.runs_out is None
    assert plan.left_at_end == pytest.approx(39)


def test_routine():
    rows = [meal("CPOS Worcester DC", f"10/{d:02d}/26 12:30:00 PM") for d in (1, 8, 15)]  # Thursdays
    rows += [meal("CPOS Hampshire DC", f"10/{d:02d}/26 06:00:00 PM") for d in (5, 12)]
    routine = highlights(rows).routine
    assert (routine.name, routine.weekday, routine.period, routine.times) == ("Worcester", "Thursday", "lunch", 3)


def test_no_routine_without_three_repeats():
    rows = [meal("CPOS Worcester DC", f"10/{d:02d}/26 12:30:00 PM") for d in (1, 8)]
    assert highlights(rows).routine is None


def test_streak_and_calendar():
    rows = [meal("CPOS Worcester DC", f"09/0{d}/26 12:00:00 PM") for d in (1, 2, 3)]
    rows.append(meal("CPOS Worcester DC", "09/03/26 06:00:00 PM"))
    rows.append(meal("CPOS Worcester DC", "09/10/26 12:00:00 PM"))
    rows.append(["Student Debit Plan", "09/04/26 01:41:00 PM", "X - OAK DRYER 10", "-$1.40", "$5.80"])  # not food
    h = highlights(rows)
    assert (h.streak.days, h.streak.start, h.streak.end) == (3, date(2026, 9, 1), date(2026, 9, 3))

    # Weeks run Sunday to Saturday; Sep 1 2026 is a Tuesday.
    first_week = h.calendar.weeks[0]
    assert [d.day.isoformat() for d in first_week][:3] == ["2026-08-30", "2026-08-31", "2026-09-01"]
    assert [d.count for d in first_week] == [0, 0, 1, 1, 2, 0, 0]
    assert [d.in_range for d in first_week] == [False, False, True, True, True, True, True]
    assert [d.in_streak for d in first_week] == [False, False, True, True, True, False, False]
    assert h.calendar.weeks[-1][4].day == date(2026, 9, 10)
    assert h.calendar.weeks[-1][5].in_range is False


def test_clock():
    rows = [
        meal("CPOS Worcester DC", "10/05/26 12:00:00 PM"),  # Monday
        meal("CPOS Worcester DC", "10/05/26 01:00:00 PM"),
        meal("CPOS Worcester DC", "10/06/26 02:00:00 PM"),  # Tuesday
        meal("CPOS Worcester DC", "10/12/26 07:45:00 AM"),  # Monday
        meal("CPOS Worcester DC", "10/13/26 01:15:00 AM"),  # 1am Tuesday is still Monday night
    ]
    clock = highlights(rows).clock
    assert clock.typical_lunch == time(13, 0)
    assert clock.earliest == time(7, 45)
    assert clock.latest == time(1, 15)
    assert (clock.top_day, clock.top_day_count) == ("Monday", 4)
    assert clock.hours == list(range(7, 26))  # 7am through the 1am hour
    assert clock.grid["Monday"][12] == 1 and clock.grid["Monday"][25] == 1
    assert clock.grid["Sunday"][12] == 0


def test_fun_facts():
    rows = [
        meal("CPOS Worcester DC", "10/05/26 12:00:00 PM"),
        meal("CPOS Worcester DC", "10/05/26 12:00:40 PM"),  # swiped someone in
        meal("CPOS Worcester GG", "10/05/26 12:01:00 PM"),  # different place: not a double
        meal("CPOS Hampshire DC", "10/06/26 06:00:00 PM"),
        dollars("CPOS Tamales", "10/06/26 07:00:00 PM", 9.5, 90.5),
        ["Student Debit Plan", "10/06/26 01:41:00 PM", "X - OAK DRYER 10", "-$1.40", "$5.80"],
    ]
    fun = highlights(rows).fun
    assert fun.double_swipes == 1
    assert fun.places_tried == 3  # Worcester (incl. Grab 'n Go), Hamp, Tamales
    assert fun.busiest_day == date(2026, 10, 5)
    assert fun.busiest_day_count == 3
    assert fun.busiest_day_places == ["Worcester", "Worcester Grab 'n Go"]


def test_plans_without_spending_do_not_crash():
    # Charges that parse to $0 but a balance that still went down.
    rows = [["UMass Dining Dollars", f"09/0{d}/26 12:00:00 PM", "CPOS Wasabi", "-$0.00", f"${100 - d}.00"] for d in range(1, 7)]
    assert highlights(rows).plans == []


def test_plan_that_would_last_for_centuries():
    rows = [dollars("CPOS Wasabi", f"09/0{d}/26 12:00:00 PM", 0.01, 1e9 - d / 100) for d in range(1, 7)]
    [plan] = highlights(rows).plans
    assert plan.runs_out is None
    assert plan.left_at_end > 0


@pytest.mark.parametrize("name, expected", [
    ("Tamales", "Tamales"),
    ("Yum Bakery", "Yum! Bakery"),
    ("People's Organic Coffee", "People's Organic Coffee"),
    ("Peoples Organic Coffee", "People's Organic Coffee"),
    ("Paciugo Gelato", "Paciugo"),
    ("Harvest Market", None),
    ("Peet's Coffee & Tea", None),
    ("Worcester", None),
])
def test_blue_wall_names(name, expected):
    assert blue_wall_name(name) == expected


def ycmp(location, when):
    return meal(location, when, account="T YCMP Commuter 155", balance="100")


def test_blue_wall_recap():
    rows = [ycmp("CPOS Tamales", f"10/0{d}/26 12:00:00 PM") for d in (1, 2, 3)]
    rows += [ycmp("CPOS Green Fields", f"10/0{d}/26 06:00:00 PM") for d in (4, 5, 6)]  # tie, but more recent
    rows += [ycmp("CPOS Wasabi", "10/07/26 01:00:00 PM")]
    rows += [ycmp("CPOS Harvest Market", f"10/0{d}/26 01:30:00 PM") for d in (1, 2)]   # not Blue Wall
    rows += [dollars("CPOS Tamales", "10/08/26 12:00:00 PM", 9.5, 80)]                 # dollars, not a swipe
    bw = highlights(rows).blue_wall
    assert bw.total == 7
    assert [(s.name, s.swipes) for s in bw.spots] == [("Green Fields", 3), ("Tamales", 3), ("Wasabi", 1)]
    assert bw.top.name == "Green Fields"
    assert "3" in bw.remark
    assert (bw.tried, bw.of) == (3, 9)
    assert bw.spots[0].share == 1 and bw.spots[2].share == pytest.approx(1 / 3)


def test_no_blue_wall_recap_under_three_swipes():
    rows = [ycmp("CPOS Tamales", "10/01/26 12:00:00 PM"), ycmp("CPOS Wasabi", "10/02/26 12:00:00 PM")]
    assert highlights(rows).blue_wall is None


def test_remarks_handle_one_swipe():
    rows = [ycmp(f"CPOS {place}", f"10/0{d}/26 12:00:00 PM") for d, place in [(1, "Tavola"), (2, "Tamales"), (3, "Wasabi")]]
    remark = highlights(rows).blue_wall.remark
    assert "1 " in remark and "1 swipes" not in remark


def test_harvest_market_card_from_five_swipes():
    five = [ycmp("CPOS Harvest Market", f"10/0{d}/26 12:00:00 PM") for d in range(1, 6)]
    harvest = highlights(five).harvest
    assert harvest.swipes == 5
    assert "5" in harvest.remark
    assert highlights(five[:4]).harvest is None


def test_top_ups():
    rows = []
    for d in range(1, 6):  # five Harvest Market top-ups: $4, $5, $6, $7, $8
        rows += [ycmp("CPOS Harvest Market", f"10/0{d}/26 12:00:00 PM"),
                 dollars("CPOS Harvest Market", f"10/0{d}/26 12:00:09 PM", 3 + d, 100 - d)]
    rows += [ycmp("CPOS Tamales", "10/07/26 01:00:00 PM"), dollars("CPOS Tamales", "10/07/26 01:00:05 PM", 1.25, 50)]
    rows += [ycmp("CPOS Wasabi", "10/08/26 01:00:00 PM"), dollars("CPOS Wasabi", "10/08/26 01:00:05 PM", 2, 48)]
    rows += [ycmp("CPOS Deli Delish", "10/09/26 01:00:00 PM"), dollars("CPOS Deli Delish", "10/09/26 01:00:05 PM", 3, 45)]
    rows += [dollars("CPOS Tavola", "10/09/26 06:00:00 PM", 10, 35)]  # bought on its own
    t = highlights(rows).top_ups
    assert t.count == 8
    assert t.total == pytest.approx(36.25)
    assert [(p.name, p.count) for p in t.places] == [("Harvest Market", 5), ("Deli Delish", 1), ("Wasabi", 1)]
    assert t.places[0].average == pytest.approx(6.00)


def test_no_top_up_screen_under_three():
    rows = [ycmp("CPOS Tamales", "10/07/26 01:00:00 PM"), dollars("CPOS Tamales", "10/07/26 01:00:05 PM", 1.25, 50)]
    assert highlights(rows).top_ups is None


def test_a_topped_up_swipe_is_one_visit_everywhere():
    rows = []
    for d in (5, 6):
        rows += [ycmp("CPOS Harvest Market", f"10/0{d}/26 12:00:00 PM"),
                 dollars("CPOS Harvest Market", f"10/0{d}/26 12:00:09 PM", 4, 100 - d)]
    rows += [ycmp("CPOS Tamales", "10/06/26 06:00:00 PM")]
    h = highlights(rows)
    assert [d.count for d in h.calendar.weeks[0] if d.in_range] == [1, 2]
    assert (h.fun.busiest_day, h.fun.busiest_day_count) == (date(2026, 10, 6), 2)
    assert h.clock.grid["Monday"][12] == 1

from datetime import datetime

import pytest

from wrapped.transactions import ParseError, account_history, balance_gaps, clean, count_rows, first_name, printed_date, parse_pdfs, parse_timestamp, rows_from_pdf

from .conftest import charge, make_history_pdf, swipe


def test_reads_rows_from_pdf_and_skips_headers():
    rows = [swipe("HampDC2", f"March {d}, 2024, 12:21PM") for d in range(1, 41)]
    pdf = make_history_pdf(rows)  # 40 rows spans two pages, each with its own header
    assert rows_from_pdf(pdf) == rows


def test_keeps_spaces_when_words_are_drawn_separately():
    rows = [
        swipe("HampDC2", "08/20/26 11:01:16 AM"),
        charge("Blue Wall 1", "09/02/26 01:15:00 PM", 9.5),
    ]
    assert rows_from_pdf(make_history_pdf(rows, word_by_word=True)) == rows


def test_count_rows():
    rows = [swipe("CPOS Worcester DC", f"09/{d:02d}/26 12:00:00 PM") for d in range(1, 21)]
    assert count_rows(make_history_pdf(rows, word_by_word=True)) == 20
    assert count_rows(make_history_pdf([])) == 0
    with pytest.raises(ParseError):
        count_rows(b"not a pdf")


def test_rejects_files_that_are_not_pdfs():
    with pytest.raises(ParseError):
        parse_pdfs([b"definitely not a pdf"])


@pytest.mark.parametrize("text, expected", [
    ("March 15, 2024, 12:21PM", datetime(2024, 3, 15, 12, 21)),
    ("March 5, 2024, 9:03AM extra junk", datetime(2024, 3, 5, 9, 3)),
    ("12/13/23 06:49:03 PM", datetime(2023, 12, 13, 18, 49, 3)),
])
def test_parses_old_and_new_timestamp_formats(text, expected):
    assert parse_timestamp(text) == expected


def test_unknown_timestamp_is_none():
    assert parse_timestamp("sometime last week") is None


def test_clean_keeps_only_spending_and_classifies_it():
    tx = clean([
        swipe("WorcDC1", "12/13/23 12:00:00 PM"),
        charge("The Grill 2", "12/13/23 06:49:03 PM", 19.50),
        ["Student Debit Plan", "12/13/23 01:41:00 PM", "X - OAK DRYER 10", "-$1.40", "$5.80"],
        ["Student Debit Plan", "12/05/23 08:28:20 AM", "GET FUNDS DEPOSITS", "+$10.00", "$10.00"],
        ["MC 2641", "12/05/23 08:28:19 AM", "Deposit to Student Debit Plan", "-$10.00", "$0.00"],
        ["UMass Dining Dollars", "12/06/23 10:00:00 AM", "Wasabi 1", "+$5.00", "$105.00"],  # refund
    ])

    assert tx["location"].tolist() == ["WorcDC1", "X - OAK DRYER 10", "The Grill 2"]
    assert tx["kind"].tolist() == ["hall", "laundry", "vendor"]
    assert tx["hall"].tolist()[0] == "Worcester"
    assert tx["place"].tolist() == ["WorcDC", "X - OAK DRYER", "The Grill"]
    assert tx["terminal"].tolist() == ["1", "10", "2"]
    assert tx["is_swipe"].tolist() == [True, False, False]
    assert tx["amount"].tolist() == [1.0, 1.4, 19.5]


def test_overlapping_pdfs_count_a_transaction_once():
    shared = swipe("WorcDC1", "12/13/23 12:00:00 PM")
    first = make_history_pdf([swipe("HampDC2", "12/12/23 08:00:00 AM"), shared])
    second = make_history_pdf([shared, swipe("BerkDC1", "12/14/23 06:00:00 PM")])
    assert parse_pdfs([first, second])["location"].tolist() == ["HampDC2", "WorcDC1", "BerkDC1"]


def test_identical_rows_in_one_pdf_are_separate_purchases():
    # Unlimited plans never change the balance and old exports only go to the minute,
    # so two swipes at once (bringing a friend) look identical.
    twice = swipe("WorcDC2", "March 4, 2024, 12:21PM")
    tx = parse_pdfs([make_history_pdf([twice, twice]), make_history_pdf([twice, twice])])
    assert len(tx) == 2


def test_count_rows_matches_the_parser():
    rows = [swipe("CPOS Worcester DC", f"09/{d:02d}/26 12:00:00 PM") for d in range(1, 18)]
    pdf = make_history_pdf(rows, word_by_word=True)
    assert count_rows(pdf) == len(rows_from_pdf(pdf)) == 17


def test_marks_dining_dollar_top_ups_on_a_swipe():
    tx = clean([
        swipe("CPOS Tamales 1", "10/05/26 12:00:00 PM"),
        charge("CPOS Tamales 2", "10/05/26 12:00:45 PM", 2.50),  # same place, 45s later
        charge("CPOS Tamales 1", "10/05/26 12:02:30 PM", 3.00),  # 2.5 minutes later
        charge("CPOS Wasabi 1", "10/05/26 12:00:10 PM", 9.00),   # different place
        swipe("CPOS Worcester DC", "10/06/26 06:00:00 PM"),
        charge("CPOS Worcester DC", "10/06/26 06:00:05 PM", 1.00),  # dining halls don't count
    ])
    top_ups = tx.loc[tx["is_top_up"], ["location", "amount"]].values.tolist()
    assert top_ups == [["CPOS Tamales 2", 2.50]]
    assert not tx.loc[tx["is_swipe"], "is_top_up"].any()


def test_balance_gaps_find_missing_purchases():
    rows = [
        ["UMass Dining Dollars", "10/04/26 03:26:31 PM", "CPOS Roots Cafe", "-$6.50", "$243.50"],
        ["UMass Dining Dollars", "10/12/26 12:47:15 PM", "CPOS Roots Cafe", "-$11.00", "$232.50"],
        ["UMass Dining Dollars", "10/15/26 03:45:52 PM", "CPOS Peoples Organic Coffee", "-$6.50", "$219.50"],
        ["E Unlimited 250", "10/13/26 07:47:20 PM", "CPOS Worcester DC", "-1", "501"],
        ["E Unlimited 250", "10/15/26 11:55:03 AM", "CPOS Worcester GG", "-1", "495"],
    ]
    gaps = balance_gaps(account_history(rows))
    assert [(g.account, g.missing) for g in gaps] == [("E Unlimited 250", 5), ("UMass Dining Dollars", 6.5)]


def test_balance_gaps_ignore_deposits_reloads_and_same_second_purchases():
    rows = [
        ["UMass Dining Dollars", "08/20/26 07:47:19 AM", "Meal Plan Office", "+$250.00", "$250.00"],
        ["UMass Dining Dollars", "09/01/26 12:00:00 PM", "CPOS Wasabi", "-$10.00", "$240.00"],
        # Two items rung up in the same second, listed in either order.
        ["UMass Dining Dollars", "09/02/26 12:00:00 PM", "CPOS Tamales", "-$2.00", "$228.00"],
        ["UMass Dining Dollars", "09/02/26 12:00:00 PM", "CPOS Tamales", "-$10.00", "$230.00"],
        # Free Friday gets topped back up each week with no row for it.
        ["Free Friday DC", "09/04/26 12:00:00 PM", "CPOS Hampshire DC", "-1", "0"],
        ["Free Friday DC", "09/11/26 12:00:00 PM", "CPOS Hampshire DC", "-1", "0"],
    ]
    assert balance_gaps(account_history(rows)) == []


def test_balance_gaps_handle_meal_plan_setup_rows():
    # The Meal Plan Office logs a "+0" next to the real deposit, in the same second.
    rows = [
        ["C Basic Plan", "08/20/26 07:51:18 AM", "Meal Plan Office", "+0", "209"],
        ["C Basic Plan", "08/20/26 07:51:18 AM", "Meal Plan Office", "+209", "209"],
        ["C Basic Plan", "08/20/26 11:00:02 AM", "PatronImport Location", "-209", "0"],
        ["C Basic Plan", "08/20/26 02:09:09 PM", "Meal Plan Office", "+0", "209"],
        ["C Basic Plan", "08/20/26 02:09:09 PM", "Meal Plan Office", "+209", "209"],
        ["C Basic Plan", "09/02/26 08:16:44 PM", "CPOS Hampshire DC", "-1", "208"],
    ]
    assert balance_gaps(account_history(rows)) == []


def test_printed_date():
    from datetime import date
    assert printed_date(make_history_pdf([], printed=date(2026, 10, 19))) == date(2026, 10, 19)
    assert printed_date(make_history_pdf([])) is None


def test_first_name():
    # GET writes "FIRST  LAST" (two spaces with no middle name) or "FIRST MIDDLE LAST".
    assert first_name(make_history_pdf([], name="JORDAN  SMITH")) == "Jordan"
    assert first_name(make_history_pdf([], name="MARY-KATE ANN LEE")) == "Mary-Kate"
    assert first_name(make_history_pdf([])) is None

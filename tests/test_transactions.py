from datetime import datetime

import pytest

from wrapped.transactions import ParseError, clean, parse_pdfs, parse_timestamp, rows_from_pdf

from .conftest import charge, make_history_pdf, swipe


def test_reads_rows_from_pdf_and_skips_headers():
    rows = [swipe("HampDC2", f"March {d}, 2024, 12:21PM") for d in range(1, 41)]
    pdf = make_history_pdf(rows)  # 40 rows spans two pages, each with its own header
    assert rows_from_pdf(pdf) == rows


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
        swipe("WorcDC1", "12/13/23 12:00:00 PM"),  # duplicate from overlapping downloads
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

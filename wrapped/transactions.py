"""Turn GET transaction-history PDFs into one clean DataFrame of charges.

Everything happens in memory: PDFs come in as bytes and are never written to disk.
"""
import re
from datetime import datetime

import fitz
import pandas as pd

HEADER_CELL = "Account Name:"
RAW_COLUMNS = ["account", "timestamp", "location", "amount", "balance"]

# Money moving between accounts, not spending.
NOT_SPENDING = r"GET FUNDS DEPOSITS|Deposit to Student Debit Plan|PatronImport Location|Meal Plan Office"

# GET has changed its date format at least once ("March 15, 2024, 12:21PM" in 2024,
# "12/13/23 06:49:03 PM" by 2026), so accept both.
TIMESTAMP_FORMATS = (
    "%B %d, %Y, %I:%M%p",
    "%B %d, %Y, %I:%M %p",
    "%m/%d/%y %I:%M:%S %p",
    "%m/%d/%y %I:%M %p",
    "%m/%d/%Y %I:%M:%S %p",
)

# Card-swipe terminals are named like "HampDC3"; the number is the register.
DINING_HALLS = {"HampDC": "Hamp", "WorcDC": "Worcester", "BerkDC": "Berk", "FrankDC": "Frank"}


class ParseError(ValueError):
    """Raised with a message that is safe to show the user."""


def rows_from_pdf(data: bytes) -> list[list[str]]:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise ParseError("One of those files isn't a readable PDF.") from e

    rows = []
    with doc:
        for page in doc:
            for table in page.find_tables().tables:
                for row in table.extract():
                    if len(row) != len(RAW_COLUMNS) or row[0] == HEADER_CELL:
                        continue
                    rows.append([(cell or "").strip() for cell in row])
    return rows


def parse_pdfs(pdfs) -> pd.DataFrame:
    """Parse one or more history PDFs (bytes) into a single clean transactions frame."""
    rows = []
    for data in pdfs:
        rows.extend(rows_from_pdf(data))
    return clean(rows)


def parse_timestamp(text: str):
    # Older PDFs sometimes had junk after the AM/PM marker.
    text = re.sub(r"(AM|PM).*$", r"\1", text.strip())
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def clean(rows: list[list[str]]) -> pd.DataFrame:
    """Normalize raw table rows into one row per charge.

    Columns: timestamp, account, location, place, terminal, amount, is_swipe, kind, hall
    """
    raw = pd.DataFrame(rows, columns=RAW_COLUMNS).astype(str)
    # History is downloaded in overlapping date windows, so the same row can show up twice.
    raw = raw.drop_duplicates()
    raw = raw[~raw["location"].str.contains(NOT_SPENDING, regex=True)]
    # Only charges ("-$12.00" or "-1" meal) count; deposits and refunds are "+".
    raw = raw[raw["amount"].str.startswith("-")]

    tx = pd.DataFrame({
        "timestamp": pd.to_datetime(raw["timestamp"].map(parse_timestamp)),
        "account": raw["account"],
        "location": raw["location"],
        "place": raw["location"].str.replace(r"[0-9]", "", regex=True).str.strip(),
        "terminal": raw["location"].str.extract(r"(\d+)\s*$", expand=False).fillna(""),
        "amount": pd.to_numeric(raw["amount"].str.replace(r"[^\d.]", "", regex=True), errors="coerce"),
        # Meal-plan accounts report amounts in meals ("-1"), money accounts in dollars ("-$9.50").
        "is_swipe": ~raw["amount"].str.contains("$", regex=False),
    })
    tx = tx.dropna(subset=["timestamp"])
    tx["hall"] = tx["place"].map(DINING_HALLS)
    tx["kind"] = "vendor"
    tx.loc[tx["hall"].notna(), "kind"] = "hall"
    tx.loc[tx["place"].str.contains("WASHER|DRYER"), "kind"] = "laundry"
    tx.loc[tx["place"].str.contains("PRNT"), "kind"] = "printing"
    return tx.sort_values("timestamp").reset_index(drop=True)

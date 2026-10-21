"""Turn GET transaction-history PDFs into one clean DataFrame of charges.

Everything happens in memory: PDFs come in as bytes and are never written to disk.
"""
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from itertools import groupby, permutations

import fitz
import pandas as pd

HEADER_CELL = "Account Name:"
# GET silently returns only the newest rows per history PDF and drops the older ones. How many
# varies by person (we've seen 14, 17 and 21).
GET_SMALLEST_LIMIT = 14
# A date window with this many transactions gets downloaded again in halves, well under the limit.
MAYBE_CUT_OFF_ROWS = 10
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

# Card-swipe terminals used to be named like "HampDC3", where the number is the register and
# register 1 at Worcester and Frank is Grab 'n Go.
DINING_HALLS = {"HampDC": "Hamp", "WorcDC": "Worcester", "BerkDC": "Berk", "FrankDC": "Frank"}
OLD_GRAB_N_GO_HALLS = {"Worcester", "Frank"}
# By Fall 2026 they're "CPOS Worcester DC", with Grab 'n Go as its own "CPOS Worcester GG".
NEW_HALL_TERMINAL = r"^CPOS (Hampshire|Worcester|Berkshire|Franklin) (DC|GG)$"
NEW_DINING_HALLS = {"Hampshire": "Hamp", "Worcester": "Worcester", "Berkshire": "Berk", "Franklin": "Frank"}
# Dining dollars paid at a vendor this close to a meal swipe there topped up the swipe (the order
# cost more than a swipe covers). In real exports the charge almost always comes 0-15s after the
# swipe, but now and then just before it, so either side counts.
TOP_UP_SECONDS = 60


class ParseError(ValueError):
    """Raised with a message that is safe to show the user."""


def open_pdf(data: bytes):
    try:
        return fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise ParseError("One of those files isn't a readable PDF.") from e


def printed_date(data: bytes) -> date | None:
    """When GET made this PDF, from its "Printed: October 19, 2026" line."""
    with open_pdf(data) as doc:
        match = re.search(r"Printed:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", doc[0].get_text() if len(doc) else "")
    return datetime.strptime(match.group(1), "%B %d, %Y").date() if match else None


def count_rows(data: bytes) -> int:
    """Number of transactions in a history PDF."""
    return transaction_count(rows_from_pdf(data))


def transaction_count(rows) -> int:
    # Leaves out leftover header rows like the wrapped "Meals)" line.
    return sum(parse_timestamp(row[1]) is not None for row in rows)


def rows_from_pdf(data: bytes) -> list[list[str]]:
    rows = []
    with open_pdf(data) as doc:
        for page in doc:
            # Read the drawn grid and put each word in its cell. page.find_tables() does the same
            # but takes ~1s a page, and its extract() glues GET's separately drawn words together
            # ("08/20/2602:09:40PM", "600\n-").
            xs, ys = grid_edges(page)
            if len(xs) != len(RAW_COLUMNS) + 1:
                continue
            words = page.get_text("words", sort=True)
            for y0, y1 in zip(ys, ys[1:]):
                row = [cell_text(words, (x0, y0, x1, y1)) for x0, x1 in zip(xs, xs[1:])]
                if any(row) and row[0] != HEADER_CELL:
                    rows.append(row)
    return rows


def grid_edges(page) -> tuple[list[float], list[float]]:
    """Column and row edges of the table, from its border lines and boxes."""
    xs, ys, top, bottom = [], [], float("inf"), float("-inf")
    for path in page.get_drawings():
        for item in path["items"]:
            if item[0] == "re":
                r = item[1]
                xs += [r.x0, r.x1]
                ys += [r.y0, r.y1]
                top, bottom = min(top, r.y0), max(bottom, r.y1)
            elif item[0] == "l":
                a, b = item[1], item[2]
                if abs(a.y - b.y) < 1:
                    ys.append(a.y)
                elif abs(a.x - b.x) < 1:
                    xs.append(a.x)
                    top, bottom = min(top, a.y, b.y), max(bottom, a.y, b.y)
    # Only horizontal lines between the top and bottom of the column borders belong to the table.
    return merge_close(xs), merge_close(y for y in ys if top - 1 <= y <= bottom + 1)


def merge_close(values, tolerance=1.0) -> list[float]:
    merged = []
    for v in sorted(values):
        if not merged or v - merged[-1] > tolerance:
            merged.append(v)
    return merged


def cell_text(words, cell) -> str:
    x0, y0, x1, y1 = cell
    return " ".join(
        w[4] for w in words
        if x0 <= (w[0] + w[2]) / 2 <= x1 and y0 <= (w[1] + w[3]) / 2 <= y1
    )


@dataclass
class BalanceGap:
    account: str
    after: datetime  # the last row before the missing ones
    missing: float   # how much the balance dropped beyond what the rows explain


def balance_gaps(rows) -> list[BalanceGap]:
    """Where an account's balance dropped by more than its rows explain: GET left rows out.

    A balance that went up unexplained is a reload with no row of its own (e.g. Free Friday's
    weekly swipe), not missing purchases, so only drops count.
    """
    gaps = []
    for account, ordered in account_history(rows).items():
        for (when, _, before), (_, change, after) in zip(ordered, ordered[1:]):
            missing = round(before + change - after, 2)
            if missing > 0:
                gaps.append(BalanceGap(account, when, missing))
    return gaps


def latest_balances(rows) -> dict[str, float]:
    """What's left on each account, from every row (deposits and Meal Plan Office ones too).

    clean() keeps only purchases, so an account nothing has been bought with yet (like an RA's
    regular dining dollars, which GET leaves until the RA ones run out) isn't in it at all.
    """
    return {account: ordered[-1][2] for account, ordered in account_history(rows).items()}


def account_history(rows) -> dict[str, list]:
    """Each account's (when, change, balance after) rows, oldest first, accounts sorted by name."""
    entries = {}
    for account, timestamp, _location, amount, balance in rows:
        when, change, after = parse_timestamp(timestamp), to_number(amount), to_number(balance)
        if when and change is not None and after is not None:
            entries.setdefault(account, []).append((when, change, after))
    return {account: chain_order(entries[account]) for account in sorted(entries)}


def chain_order(entries):
    """Sort (when, change, balance) by time. Rows in the same second come in any order (two items
    rung up together, or the Meal Plan Office's "+0" next to a deposit), so within a second use an
    order where each balance follows from the one before, if there is one."""
    ordered = []
    for _, group in groupby(sorted(entries, key=lambda e: e[0]), key=lambda e: e[0]):
        group = list(group)
        fallback = sorted(group, key=lambda e: -e[2])  # charges leave the higher balance first
        candidates = permutations(group) if len(group) <= 5 else [fallback]
        best = fallback
        for order in candidates:
            balance = ordered[-1][2] if ordered else order[0][2] - order[0][1]
            if all(abs(balance_before + e[1] - e[2]) < 0.005
                   for balance_before, e in zip([balance] + [x[2] for x in order], order)):
                best = list(order)
                break
        ordered += best
    return ordered


def to_number(text: str):
    """'-$6.50' -> -6.5, '+600' -> 600.0, '' -> None."""
    try:
        return float(re.sub(r"[^\d.+-]", "", text))
    except ValueError:
        return None


def parse_pdfs(pdfs) -> pd.DataFrame:
    """Parse one or more history PDFs (bytes) into a single clean transactions frame."""
    return clean(merge_rows([rows_from_pdf(data) for data in pdfs]))


def merge_rows(per_pdf) -> list[list[str]]:
    """Combine the rows of several PDFs.

    A row found in two PDFs (overlapping date ranges) is one transaction. Identical rows within
    one PDF are separate purchases, e.g. two swipes in the same minute on an unlimited plan,
    whose balance never changes.
    """
    merged = Counter()
    for rows in per_pdf:
        merged |= Counter(tuple(row) for row in rows)
    return [list(row) for row in merged.elements()]


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

    Columns: timestamp, account, location, place, terminal, amount, balance, is_swipe, kind, hall, grab_n_go,
    is_top_up
    """
    raw = pd.DataFrame(rows, columns=RAW_COLUMNS).astype(str)
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
        # What was left on that account afterwards, in the same unit as amount.
        "balance": pd.to_numeric(raw["balance"].str.replace(r"[^\d.-]", "", regex=True), errors="coerce"),
        # Meal-plan accounts report amounts in meals ("-1"), money accounts in dollars ("-$9.50").
        "is_swipe": ~raw["amount"].str.contains("$", regex=False),
    })
    tx = tx.dropna(subset=["timestamp"])
    new_style = tx["location"].str.extract(NEW_HALL_TERMINAL)
    tx["hall"] = tx["place"].map(DINING_HALLS).fillna(new_style[0].map(NEW_DINING_HALLS))
    tx["grab_n_go"] = new_style[1].eq("GG") | (tx["hall"].isin(OLD_GRAB_N_GO_HALLS) & tx["terminal"].eq("1"))
    tx["kind"] = "vendor"
    tx.loc[tx["hall"].notna(), "kind"] = "hall"
    tx.loc[tx["place"].str.contains("WASHER|DRYER"), "kind"] = "laundry"
    tx.loc[tx["place"].str.contains("PRNT"), "kind"] = "printing"
    tx = tx.sort_values("timestamp").reset_index(drop=True)
    tx["is_top_up"] = top_ups(tx)
    return tx


def top_ups(tx: pd.DataFrame) -> pd.Series:
    """Which rows are dining dollars paid at a vendor within TOP_UP_SECONDS of a meal swipe there."""
    vendor = tx["kind"] == "vendor"
    paid = tx.loc[vendor & ~tx["is_swipe"], ["timestamp", "place"]].reset_index()
    swipes = tx.loc[vendor & tx["is_swipe"], ["timestamp", "place"]].rename(columns={"timestamp": "swipe_time"})
    if paid.empty or swipes.empty:
        return pd.Series(False, index=tx.index)
    nearest = pd.merge_asof(
        paid, swipes, left_on="timestamp", right_on="swipe_time", by="place",
        tolerance=pd.Timedelta(seconds=TOP_UP_SECONDS), direction="nearest",
    )
    is_top_up = pd.Series(False, index=tx.index)
    is_top_up[nearest.loc[nearest["swipe_time"].notna(), "index"]] = True
    return is_top_up

import fitz
import pytest

HEADER = ["Account Name:", "Date & Time", "Activity Details", "Amount ($ / Meals)", "Balance"]
COLUMN_WIDTHS = [110, 130, 120, 100, 70]
ROWS_PER_PAGE = 30


def make_history_pdf(rows):
    """Build a fake GET history PDF: a bordered table like the real (FPDF-generated) export."""
    doc = fitz.open()
    for start in range(0, max(len(rows), 1), ROWS_PER_PAGE):
        page = doc.new_page()
        y = 60
        for row in [HEADER, *rows[start:start + ROWS_PER_PAGE]]:
            x = 30
            for text, width in zip(row, COLUMN_WIDTHS):
                page.draw_rect(fitz.Rect(x, y, x + width, y + 20), color=(0.78, 0.78, 0.78), width=0.85)
                page.insert_text((x + 4, y + 14), text, fontsize=8)
                x += width
            y += 20
    return doc.tobytes()


def swipe(location, when, account="M Unlimited DC"):
    return [account, when, location, "-1", "500"]


def charge(location, when, amount, account="UMass Dining Dollars"):
    return [account, when, location, f"-${amount:.2f}", "$100.00"]


@pytest.fixture
def history_pdf():
    return make_history_pdf

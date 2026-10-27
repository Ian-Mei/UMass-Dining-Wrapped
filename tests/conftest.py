import fitz
import pytest

HEADER = ["Account Name:", "Date & Time", "Activity Details", "Amount ($ / Meals)", "Balance"]
COLUMN_WIDTHS = [110, 130, 120, 100, 70]
ROWS_PER_PAGE = 30


def make_history_pdf(rows, word_by_word=False, printed=None, name=None):
    """Build a fake GET history PDF: a bordered table like the real (FPDF-generated) export.

    word_by_word draws each word as its own text object with no space characters between them,
    which is how the real export does it. printed adds GET's "Printed: October 19, 2026" line, and
    name the account holder's name under "UMass Amherst" (GET writes it in capitals).
    """
    doc = fitz.open()
    for start in range(0, max(len(rows), 1), ROWS_PER_PAGE):
        page = doc.new_page()
        if name:
            page.insert_text((30, 20), "UMass Amherst", fontsize=8)
            page.insert_text((30, 30), name, fontsize=8)
        if printed:
            page.insert_text((30, 40), f"Printed: {printed:%B} {printed.day}, {printed.year}", fontsize=8)
        y = 60
        for row in [HEADER, *rows[start:start + ROWS_PER_PAGE]]:
            x = 30
            for text, width in zip(row, COLUMN_WIDTHS):
                page.draw_rect(fitz.Rect(x, y, x + width, y + 20), color=(0.78, 0.78, 0.78), width=0.85)
                if word_by_word:
                    word_x = x + 4
                    for word in text.split():
                        page.insert_text((word_x, y + 14), word, fontsize=8)
                        word_x += fitz.get_text_length(word + " ", fontsize=8)
                else:
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

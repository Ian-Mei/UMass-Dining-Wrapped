import fitz
import pytest

HEADER = ["Account Name:", "Date & Time", "Activity Details", "Amount ($ / Meals)", "Balance"]
COLUMN_WIDTHS = [110, 130, 120, 100, 70]
ROWS_PER_PAGE = 30


def draw_text(page, x, y, text, word_by_word):
    if not word_by_word:
        page.insert_text((x, y), text, fontsize=8)
        return
    for word in text.split():
        page.insert_text((x, y), word, fontsize=8)
        x += fitz.get_text_length(word + " ", fontsize=8)


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
            draw_text(page, 30, 20, "UMass Amherst", word_by_word)
            draw_text(page, 30, 30, name, word_by_word)
        if printed:
            page.insert_text((30, 40), f"Printed: {printed:%B} {printed.day}, {printed.year}", fontsize=8)
        y = 60
        for row in [HEADER, *rows[start:start + ROWS_PER_PAGE]]:
            x = 30
            for text, width in zip(row, COLUMN_WIDTHS):
                page.draw_rect(fitz.Rect(x, y, x + width, y + 20), color=(0.78, 0.78, 0.78), width=0.85)
                draw_text(page, x + 4, y + 14, text, word_by_word)
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

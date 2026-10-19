import io
from urllib.parse import unquote

import pytest

from app import app

from .conftest import charge, make_history_pdf, swipe


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def upload(client, *pdfs):
    files = [(io.BytesIO(pdf), f"history-{i}.pdf") for i, pdf in enumerate(pdfs)]
    return client.post("/wrapped", data={"pdfs": files}, content_type="multipart/form-data")


def test_home_has_bookmarklet_pointing_back_at_this_site(client):
    page = client.get("/").get_data(as_text=True)
    assert 'href="javascript:' in page
    assert "http://localhost" in unquote(page)
    assert "__APP_ORIGIN__" not in unquote(page)


def test_import_page(client):
    page = client.get("/import").get_data(as_text=True)
    assert '"https://get.cbord.com"' in page


def test_wrapped_requires_a_file(client):
    response = client.post("/wrapped", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "Choose your transaction history PDF" in response.get_data(as_text=True)


def test_wrapped_rejects_garbage(client):
    response = upload(client, b"not a pdf")
    assert response.status_code == 400
    assert "readable PDF" in response.get_data(as_text=True)


def test_wrapped_from_overlapping_pdfs(client):
    first = make_history_pdf([
        swipe("WorcDC2", "March 4, 2024, 12:00PM"),
        charge("Wasabi 1", "March 5, 2024, 12:00PM", 10.00),
    ])
    second = make_history_pdf([
        charge("Wasabi 1", "March 5, 2024, 12:00PM", 10.00),  # overlap with the first window
        ["Student Debit Plan", "03/06/24 01:41:00 PM", "X - OAK DRYER 10", "-$1.40", "$5.80"],
    ])
    response = upload(client, first, second)
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Spring 24 UMass Dining Wrapped" in page
    assert "Worcester" in page
    assert "$10.00" in page  # Wasabi counted once
    assert "OAK DRYER 10" in page


def test_wrapped_without_meal_plan_skips_dining_hall_section(client):
    response = upload(client, make_history_pdf([charge("The Grill 2", "12/13/23 06:49:03 PM", 19.50)]))
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="favDC"' not in page
    assert 'id="top3vendors"' in page

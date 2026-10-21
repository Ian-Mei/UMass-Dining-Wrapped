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


def test_rows_says_when_a_window_may_be_cut_off(client):
    def check(n):
        rows = [swipe("CPOS Worcester DC", f"09/{d % 28 + 1:02d}/26 12:{d:02d}:00 PM") for d in range(n)]
        return client.post("/rows", data=make_history_pdf(rows)).get_json()

    # GET's limit varies by person (14 rows was the smallest seen), so split well below it.
    assert check(9) == {"rows": 9, "full": False}
    assert check(10) == {"rows": 10, "full": True}


def test_rows_rejects_garbage(client):
    response = client.post("/rows", data=b"not a pdf")
    assert response.status_code == 400
    assert "readable PDF" in response.get_json()["error"]


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


def test_saves_uploads_when_debugging(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.SAVE_UPLOADS_DIR", str(tmp_path))
    pdf = make_history_pdf([swipe("WorcDC2", "March 4, 2024, 12:00PM")])
    assert upload(client, pdf, b"not a pdf").status_code == 400

    [folder] = tmp_path.iterdir()
    assert (folder / "history-00.pdf").read_bytes() == pdf
    assert (folder / "history-01.pdf").read_bytes() == b"not a pdf"
    assert "readable PDF" in (folder / "error.txt").read_text()


def test_saves_traceback_when_parsing_crashes(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.SAVE_UPLOADS_DIR", str(tmp_path))
    monkeypatch.setattr("app.build_wrapped", lambda tx: 1 / 0)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    try:
        response = upload(client, make_history_pdf([swipe("WorcDC2", "March 4, 2024, 12:00PM")]))
    finally:
        app.config["PROPAGATE_EXCEPTIONS"] = None
    assert response.status_code == 500
    [folder] = tmp_path.iterdir()
    assert (folder / "history-00.pdf").exists()
    assert "ZeroDivisionError" in (folder / "error.txt").read_text()


def test_does_not_save_by_default(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    upload(client, make_history_pdf([swipe("WorcDC2", "March 4, 2024, 12:00PM")]))
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def saved_runs(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.SAVE_UPLOADS_DIR", str(tmp_path))
    run = tmp_path / "Friend One"
    run.mkdir()
    (run / "history-00.pdf").write_bytes(make_history_pdf([swipe("CPOS Worcester DC", "10/05/26 12:00:00 PM")]))
    app.debug = True
    yield tmp_path
    app.debug = False


def test_dev_pages_need_debug_mode(client, saved_runs):
    app.debug = False
    assert client.get("/dev").status_code == 404
    assert client.get("/dev/Friend One").status_code == 404


def test_dev_lists_saved_runs(client, saved_runs):
    page = client.get("/dev").get_data(as_text=True)
    assert "/dev/Friend%20One" in page


def test_dev_renders_a_saved_run(client, saved_runs):
    response = client.get("/dev/Friend One")
    assert response.status_code == 200
    assert "Fall 26 UMass Dining Wrapped" in response.get_data(as_text=True)


def test_dev_only_reads_runs_inside_the_uploads_folder(client, saved_runs):
    (saved_runs.parent / "outside").mkdir(exist_ok=True)
    assert client.get("/dev/..").status_code == 404
    assert client.get("/dev/../outside").status_code == 404
    assert client.get("/dev/missing").status_code == 404


def test_debug_mode_saves_to_debug_uploads_by_default(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("app.SAVE_UPLOADS_DIR", None)
    app.debug = True
    try:
        upload(client, make_history_pdf([swipe("WorcDC2", "March 4, 2024, 12:00PM")]))
    finally:
        app.debug = False
    [folder] = (tmp_path / "debug_uploads").iterdir()
    assert (folder / "history-00.pdf").exists()


def test_warns_when_a_pdf_may_be_cut_off(client):
    full = [swipe("CPOS Worcester DC", f"09/{d:02d}/26 12:00:00 PM") for d in range(1, 18)]
    page = upload(client, make_history_pdf(full)).get_data(as_text=True)
    assert "may be missing" in page

    page = upload(client, make_history_pdf(full[:5])).get_data(as_text=True)
    assert "may be missing" not in page


def test_bookmarklet_uses_the_public_address_behind_a_proxy(client):
    page = client.get("/", headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "wrapped.example.com"})
    assert "https://wrapped.example.com" in unquote(page.get_data(as_text=True))


def test_warns_when_a_balance_drops_more_than_the_purchases_explain(client):
    rows = [
        ["UMass Dining Dollars", "10/12/26 12:47:15 PM", "CPOS Roots Cafe", "-$11.00", "$232.50"],
        # A $6.50 purchase GET left out happened here.
        ["UMass Dining Dollars", "10/15/26 03:45:52 PM", "CPOS Peoples Organic Coffee", "-$6.50", "$219.50"],
    ]
    page = upload(client, make_history_pdf(rows)).get_data(as_text=True)
    assert "may be missing" in page

import io
from urllib.parse import unquote

import pytest

from datetime import date, timedelta

from app import app, build_from_pdfs

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
    monkeypatch.setattr("app.build_wrapped", lambda tx, **kwargs: 1 / 0)
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


def test_no_notice_for_a_busy_day_that_came_back_whole(client):
    # A one-day window can't be split further; 12 rows is still under GET's smallest limit (14).
    rows = [charge("CPOS Tamales", f"10/05/26 {h:02d}:00:00 PM", 1.00) for h in range(1, 13)]
    page = upload(client, make_history_pdf(rows)).get_data(as_text=True)
    assert "may be missing" not in page


def test_plan_pace_counts_up_to_when_the_pdf_was_printed():
    # $160 used Sep 1 - Oct 1 and $40 left; printed Oct 1 but uploaded weeks later.
    rows = [["UMass Dining Dollars", f"09/{d:02d}/26 12:00:00 PM", "CPOS Wasabi", "-$10.00", f"${200 - 10 * (i + 1)}.00"]
            for i, d in enumerate(range(1, 31, 2))]
    rows.append(["UMass Dining Dollars", "10/01/26 12:00:00 PM", "CPOS Wasabi", "-$10.00", "$40.00"])
    result, _ = build_from_pdfs([make_history_pdf(rows, printed=date(2026, 10, 1))])
    [plan] = result.highlights.plans
    assert plan.runs_out == date(2026, 10, 8)


def test_results_page_has_the_raw_data_and_the_explorer(client):
    rows = [swipe("CPOS Tamales", f"09/{d:02d}/26 06:00:00 PM", account="T YCMP Commuter 155") for d in (14, 15, 21)]
    page = upload(client, make_history_pdf(rows)).get_data(as_text=True)
    assert 'id="days"' in page and 'id="places"' in page
    assert 'id="explorer-data"' in page and '"place": "Tamales"' in page
    assert "data-explore-day" not in page  # no jumping ahead to a day; it would skip screens
    assert '"busiest": "2026-09-14"' in page  # shown in gold on the month map instead
    assert 'data-explore-place="Tamales"' in page  # from the Blue Wall reveal
    assert "All your data" in page and "Every Place" in page


def test_without_a_ycmp_plan_explore_your_places_is_only_dining_dollars(client):
    # Unlimited plans don't choose where a swipe goes, so their places are where dining dollars went.
    rows = [swipe("CPOS Tamales", f"09/{d:02d}/26 06:00:00 PM") for d in (14, 15, 21)]
    page = upload(client, make_history_pdf(rows)).get_data(as_text=True)
    assert 'id="days"' in page and 'id="places"' not in page  # no dining dollars, no places
    assert "data-explore-place" not in page
    rows.append(charge("CPOS Peet's Coffee & Tea", "09/16/26 09:00:00 AM", 4.25))
    page = upload(client, make_history_pdf(rows)).get_data(as_text=True)
    assert 'id="places"' in page and "Dining Dollars</h1>" in page
    assert 'data-explore-place="Tamales"' not in page  # Blue Wall swipes aren't in it


def test_only_laundry_still_makes_a_wrapped(client):
    rows = [["Student Debit Plan", "10/07/26 01:41:00 PM", "X - OAK DRYER 10", "-$1.40", "$5.80"]]
    assert upload(client, make_history_pdf(rows)).status_code == 200


def test_raw_data_leaves_late_night_blank_where_there_is_none(client):
    rows = [swipe("CPOS Hampshire DC", "09/14/26 12:00:00 PM"), swipe("CPOS Worcester DC", "09/14/26 01:00:00 PM")]
    page = upload(client, make_history_pdf(rows)).get_data(as_text=True)
    tables = page[page.index("All your data"):]
    assert "<td></td>" in tables          # Hamp has no late night
    assert "<td>&ndash;</td>" in tables   # Worcester does, they just didn't go


def lunches(n):
    return [swipe("CPOS Worcester DC" if d % 2 else "CPOS Hampshire DC", f"09/{d + 1:02d}/26 12:00:00 PM", "C Basic Plan")
            for d in range(n)]


def test_personality_wheel_has_every_personality_and_dims_the_ones_they_did_not_get(client):
    page = upload(client, make_history_pdf(lunches(30))).get_data(as_text=True)  # a Lunch Lord
    assert page.count('class="wheelcard') == 19
    assert page.count('class="wheelcard locked"') == 18
    assert 'data-name="Lunch Lord"' in page and 'data-name="Average Joe"' not in page
    assert "See what other personalities you got" not in page  # only the one


def test_average_joe_is_on_the_wheel_only_for_people_who_got_it(client):
    page = upload(client, make_history_pdf(lunches(5))).get_data(as_text=True)
    assert page.count('class="wheelcard') == 20
    assert page.count('class="wheelcard locked"') == 19
    assert 'data-name="Average Joe"' in page


def test_see_other_personalities_when_there_are_several(client):
    weekdays = [d for d in range(42) if d % 7 < 5]  # Sep 7 2026 is a Monday
    rows = [swipe("CPOS Worcester DC" if d % 2 else "CPOS Hampshire DC",
                  (date(2026, 9, 7) + timedelta(days=d)).strftime("%m/%d/%y 12:00:00 PM"), "C Basic Plan") for d in weekdays]
    rows += [charge("CPOS Peets Coffee", (date(2026, 9, 7) + timedelta(days=d)).strftime("%m/%d/%y 09:00:00 AM"), 4.50)
             for d in weekdays if d % 7 < 4]
    page = upload(client, make_history_pdf(rows)).get_data(as_text=True)
    assert page.count('class="wheelcard locked"') == 16  # 19 less Coffee Addict, Weekend Ghost and Lunch Lord
    assert "See what other personalities you got" in page
    assert '["Coffee Addict", "Weekend Ghost", "Lunch Lord"]' in page.replace("&#34;", '"')
    assert 'data-reason="100% of your meal swipes were at lunch."' in page
    assert '<p class="wheelreason">You made about' in page  # the main one's, before the wheel lands

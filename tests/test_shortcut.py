"""The iPhone Shortcut: its script, the /import box it opens on GET, and the home page steps."""
from pathlib import Path

import app as app_module

from .test_app import client  # noqa: F401  (client is a fixture)

ICLOUD = "https://www.icloud.com/shortcuts/made-up-link"


def test_shortcut_script_points_back_at_this_site(client):
    res = client.get("/shortcut.js", base_url="https://wrapped.example")
    code = res.get_data(as_text=True)
    assert res.mimetype == "text/plain"
    assert 'const APP = "https://wrapped.example";' in code
    assert "__APP_ORIGIN__" not in code
    assert code.rstrip().endswith("})();")


def test_shortcut_script_ignores_a_forged_forwarded_host(client):
    code = client.get("/shortcut.js", base_url="https://wrapped.example",
                      headers={"X-Forwarded-Host": "evil.example"}).get_data(as_text=True)
    assert "evil.example" not in code


def test_only_get_can_put_the_import_page_in_a_box(client):
    res = client.get("/import")
    assert res.headers["Content-Security-Policy"] == "frame-ancestors https://get.cbord.com"


def test_import_page_hands_the_pdfs_back_when_its_in_a_box(client):
    page = client.get("/import").get_data(as_text=True)
    assert "window.opener || (IN_FRAME ? window.parent : null)" in page
    assert 'HOME.postMessage({ type: "done", pdfs }, GET_ORIGIN, pdfs);' in page
    assert "event.source !== HOME" in page


def test_no_iphone_steps_until_the_shortcut_link_is_set(client, monkeypatch):
    monkeypatch.setattr(app_module, "SHORTCUT_URL", None)
    page = client.get("/").get_data(as_text=True)
    assert 'class="home-iphone"' not in page
    assert "is-iphone" not in page
    assert "do the GET\n" in page or "so do the GET" in page


def test_iphone_steps_link_to_the_shortcut(client, monkeypatch):
    monkeypatch.setattr(app_module, "SHORTCUT_URL", ICLOUD)
    page = client.get("/").get_data(as_text=True)
    steps = page[page.index('class="home-iphone"'):page.index("<!-- /iphone -->")]
    assert f'href="{ICLOUD}"' in steps and "Add to iPhone" in steps
    assert "Allow Running Scripts" in steps
    assert "tap Share, then <b>Dining Wrapped</b>" in steps
    assert "get.cbord.com/umass/full/funds_home.php" in steps
    assert "/iPhone/.test(navigator.userAgent)" in page
    assert "Add to iPhone button" in page  # the FAQ points at it


def test_iphones_see_their_steps_instead_of_the_bookmark():
    css = (Path(__file__).parent.parent / "static" / "styles" / "home.css").read_text(encoding="utf8")
    assert ".home-iphone { display: none;" in css
    assert ".is-iphone .home-iphone { display: block; }" in css
    assert ".is-iphone .home-howto { display: none; }" in css

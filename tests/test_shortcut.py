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
    assert "older iPhones: Settings &rsaquo; Shortcuts &rsaquo; Advanced" in steps
    # Newer iOS puts Share in the menu by the address and the Shortcut under View More.
    assert "tap Share (on newer iPhones it's in the menu by the address), then <b>Dining Wrapped</b>" in steps
    assert "Tap <b>Allow</b> the first time." in steps
    assert "get.cbord.com/umass/full/funds_home.php" in steps
    assert "/iPhone/.test(navigator.userAgent)" in page
    assert "Add to iPhone button" in page  # the FAQ points at it


def test_iphones_see_their_steps_instead_of_the_bookmark():
    css = (Path(__file__).parent.parent / "static" / "styles" / "home.css").read_text(encoding="utf8")
    assert ".home-iphone { display: none;" in css
    assert ".is-iphone .home-iphone { display: block; }" in css
    assert ".is-iphone .home-howto { display: none; }" in css


def test_import_box_has_room_for_a_three_line_error():
    code = (Path(__file__).parent.parent / "static" / "scripts" / "shortcut.js").read_text(encoding="utf8")
    assert "height:132px" in code


def test_progress_bar_never_moves_backward(client):
    page = client.get("/import").get_data(as_text=True)
    assert "furthest = Math.max(furthest, done / total)" in page


def test_empty_upload_message_fits_the_bookmark_and_the_shortcut(client):
    res = client.post("/wrapped", data={}, content_type="multipart/form-data")
    page = res.get_data(as_text=True)
    assert "Run Dining Wrapped again from GET." in page
    assert "bookmark again" not in page


def test_iphone_steps_show_a_gif_of_the_shortcut(client, monkeypatch):
    monkeypatch.setattr(app_module, "SHORTCUT_URL", ICLOUD)
    page = client.get("/").get_data(as_text=True)
    steps = page[page.index('class="home-iphone"'):page.index("<!-- /iphone -->")]
    demo = steps[steps.index('class="home-iphone-demo"'):steps.index("</figure>")]
    assert "imgs/how-to-iphone.gif" in demo
    assert 'media="(prefers-reduced-motion: reduce)"' in demo and "imgs/how-to-iphone-still.png" in demo
    assert 'loading="lazy"' in demo  # laptops never show this section, so they skip it
    assert 'alt="How it works on iPhone: in Safari on GET' in demo


def test_iphone_gif_is_small():
    gif = Path(__file__).parent.parent / "static" / "styles" / "imgs" / "how-to-iphone.gif"
    assert gif.read_bytes()[:6] == b"GIF89a"
    assert gif.stat().st_size < 1_000_000
    css = (Path(__file__).parent.parent / "static" / "styles" / "home.css").read_text(encoding="utf8")
    rules = css.splitlines()
    assert any(rule.startswith(".home-iphone-demo { width: min(240px, 70%);") for rule in rules)
    assert any(rule.startswith(".home-iphone .home-iphone-button { display: block;") for rule in rules)  # beats the black hero button

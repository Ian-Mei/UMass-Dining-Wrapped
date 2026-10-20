import os
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from flask import Flask, abort, jsonify, render_template, render_template_string, request
from waitress import serve

from wrapped import ParseError, build_wrapped, parse_pdfs
from wrapped.transactions import count_rows

GET_ORIGIN = "https://get.cbord.com"
MAX_UPLOAD_MB = 25
# GET silently returns only the newest page of rows (17 when we checked) per history PDF, so a
# date window this full may be missing its oldest rows and gets downloaded again in halves.
WINDOW_FULL_ROWS = 15
BOOKMARKLET_SOURCE = Path(__file__).parent / "static" / "scripts" / "bookmarklet.js"
# Local debugging only: when set, every upload is saved here (plus a traceback if it crashes).
# Never set this on a public deployment; it stores people's transaction history.
SAVE_UPLOADS_DIR = os.environ.get("WRAPPED_SAVE_UPLOADS")
# In debug mode (flask --app app run --debug) uploads are saved here unless the above is set.
DEBUG_UPLOADS_DIR = "debug_uploads"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


@app.template_filter()
def clock_time(t):
    return f"{t:%I:%M %p}".lstrip("0")  # 1:06 PM


@app.template_filter()
def short_date(d):
    return f"{d:%b} {d.day}"  # Sep 6


@app.template_filter()
def hour_label(hour):
    """Grid hour (past midnight is 24, 25, ...) as 9a, 12p, 1a."""
    h = hour % 24
    return f"{h % 12 or 12}{'a' if h < 12 else 'p'}"


def public_origin():
    # Set WRAPPED_PUBLIC_URL when running behind a proxy so the bookmarklet points at the right host.
    return os.environ.get("WRAPPED_PUBLIC_URL", request.host_url).rstrip("/")


def bookmarklet_href():
    lines = BOOKMARKLET_SOURCE.read_text(encoding="utf-8").splitlines()
    code = " ".join(line.strip() for line in lines if line.strip() and not line.strip().startswith("//"))
    return "javascript:" + quote(code.replace("__APP_ORIGIN__", public_origin()), safe="")


def render_home(error=None, status=200):
    return render_template("home.html", bookmarklet=bookmarklet_href(), error=error), status


@app.get("/")
def home():
    return render_home()


@app.get("/import")
def import_from_get():
    """Opened by the bookmarklet; receives the history PDFs from the GET tab."""
    return render_template("import.html", get_origin=GET_ORIGIN)


@app.post("/rows")
def rows():
    """Called by /import for each downloaded window: how many rows, and might it be cut off?"""
    try:
        n = count_rows(request.get_data())
    except ParseError as e:
        return jsonify(error=str(e)), 400
    return jsonify(rows=n, full=n >= WINDOW_FULL_ROWS)


def uploads_dir():
    """Where uploads get saved, or None to not save them."""
    return SAVE_UPLOADS_DIR or (DEBUG_UPLOADS_DIR if app.debug else None)


def save_upload(pdfs):
    """Save the PDFs before parsing, so they survive a crash. Returns the folder."""
    folder = Path(uploads_dir()) / datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    folder.mkdir(parents=True)
    for i, pdf in enumerate(pdfs):
        (folder / f"history-{i:02d}.pdf").write_bytes(pdf)
    app.logger.warning("Saved %d uploaded PDFs to %s", len(pdfs), folder)
    return folder


@app.post("/wrapped")
def wrapped():
    pdfs = [f.read() for f in request.files.getlist("pdfs") if f.filename]
    if not pdfs:
        return render_home("Choose your transaction history PDF first.", 400)
    saved_to = save_upload(pdfs) if uploads_dir() else None
    try:
        result = build_wrapped(parse_pdfs(pdfs))
    except ParseError as e:
        if saved_to:
            (saved_to / "error.txt").write_text(f"ParseError: {e}\n", encoding="utf-8")
        return render_home(str(e), 400)
    except Exception:
        if saved_to:
            (saved_to / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    return render_wrapped(result)


def render_wrapped(result):
    vendor_table_html = (
        result.vendors.rename(columns=str.title).rename_axis(None)
        .to_html(classes="data", formatters={"Spent": "${:.2f}".format})
    )
    return render_template("wrapped.html", w=result, vendor_table_html=vendor_table_html)


# Dev only (flask --app app run --debug): re-render saved uploads without going through GET.
DEV_RUNS_INDEX = """<!doctype html><title>Saved runs</title>
<h1>Saved runs in {{ folder }}</h1>
<ul>{% for run, failed in runs %}<li><a href="{{ url_for('dev_run', run=run) }}">{{ run }}</a>{% if failed %} (failed){% endif %}</li>
{% else %}<li>None yet. Upload something and it will show up here.</li>{% endfor %}</ul>"""


def dev_runs_dir():
    if not app.debug:
        abort(404)
    return Path(uploads_dir())


@app.get("/dev")
def dev_runs():
    folder = dev_runs_dir()
    runs = sorted(p for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else []
    return render_template_string(DEV_RUNS_INDEX, folder=folder, runs=[(p.name, (p / "error.txt").exists()) for p in runs])


@app.get("/dev/<path:run>")
def dev_run(run):
    folder = dev_runs_dir().resolve()
    run_dir = (folder / run).resolve()
    if run_dir.parent != folder or not run_dir.is_dir():
        abort(404)
    result = build_wrapped(parse_pdfs([p.read_bytes() for p in sorted(run_dir.glob("*.pdf"))]))
    return render_wrapped(result)


@app.errorhandler(413)
def too_large(_):
    return render_home(f"That upload is over {MAX_UPLOAD_MB} MB. A semester of history should be much smaller.", 413)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Serving on http://localhost:{port}")
    serve(app, host="0.0.0.0", port=port)

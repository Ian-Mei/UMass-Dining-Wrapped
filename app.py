import os
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from flask import Flask, abort, jsonify, render_template, render_template_string, request
from waitress import serve

from wrapped import ParseError, build_wrapped
from wrapped.personality import wheel_cards
from wrapped.transactions import (
    GET_SMALLEST_LIMIT, MAYBE_CUT_OFF_ROWS, account_history, balance_gaps, clean, count_rows, first_name, merge_rows, printed_date,
    rows_from_pdf, transaction_count,
)

GET_ORIGIN = "https://get.cbord.com"
MAX_UPLOAD_MB = 25
BOOKMARKLET_SOURCE = Path(__file__).parent / "static" / "scripts" / "bookmarklet.js"
# Local debugging only: when set, every upload is saved here (plus a traceback if it crashes).
# Never set this on a public deployment; it stores people's transaction history.
SAVE_UPLOADS_DIR = os.environ.get("WRAPPED_SAVE_UPLOADS")
# In debug mode (flask --app app run --debug) uploads are saved here unless the above is set.
DEBUG_UPLOADS_DIR = "debug_uploads"
# Visit counts (templates/_goatcounter.html). Only the deploy sets it (render.yaml), so local runs
# and forks don't count.
GOATCOUNTER_URL = os.environ.get("WRAPPED_GOATCOUNTER_URL")
# Linked from the home page FAQ and the last results screen.
FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdJ23vnh_7Q0eL2NI6415G-4VDRiZK-JZpBnH_FGAPRVQapxg/viewform"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
# Behind a proxy (Render), take https from X-Forwarded-Proto so the bookmarklet's origin check
# matches the page it opens. Not X-Forwarded-Host: anyone can send it, and it would decide where
# the bookmarklet sends people's PDFs. Render keeps the real Host; elsewhere set WRAPPED_PUBLIC_URL.
SERVE_OPTIONS = {"host": "0.0.0.0", "trusted_proxy": "*", "trusted_proxy_headers": {"x-forwarded-proto"}}


@app.context_processor
def analytics():
    return {"goatcounter": GOATCOUNTER_URL}


@app.context_processor
def feedback():
    return {"feedback_url": FEEDBACK_URL}


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
    # WRAPPED_PUBLIC_URL overrides the address the request came in on (e.g. if the proxy
    # changes the Host header or doesn't send X-Forwarded-Proto).
    return os.environ.get("WRAPPED_PUBLIC_URL", request.host_url).rstrip("/")


def load_bookmarklet():
    """bookmarklet.js squeezed onto one line, still with the __APP_ORIGIN__ placeholder."""
    lines = BOOKMARKLET_SOURCE.read_text(encoding="utf-8").splitlines()
    return " ".join(line.strip() for line in lines if line.strip() and not line.strip().startswith("//"))


BOOKMARKLET_CODE = load_bookmarklet()


def bookmarklet_href():
    # In debug mode, re-read the file so edits show up without a restart.
    code = load_bookmarklet() if app.debug else BOOKMARKLET_CODE
    return "javascript:" + quote(code.replace("__APP_ORIGIN__", public_origin()), safe="")


def render_home(error=None, status=200, count_path="/"):
    page = render_template("home.html", bookmarklet=bookmarklet_href(), error=error, count_path=count_path)
    return page, status


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
    # A full window gets downloaded again in halves.
    return jsonify(rows=n, full=n >= MAYBE_CUT_OFF_ROWS)


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
        result, maybe_cut_off = build_from_pdfs(pdfs)
    except ParseError as e:
        if saved_to:
            (saved_to / "error.txt").write_text(f"ParseError: {e}\n", encoding="utf-8")
        return render_home(str(e), 400, count_path="/error")
    except Exception:
        if saved_to:
            (saved_to / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    return render_wrapped(result, maybe_cut_off, name_on(pdfs))


def build_from_pdfs(pdfs):
    """The Wrapped for these PDFs, and whether GET may have left rows out of them.

    Two signs: a PDF as full as GET's smallest limit (catches a whole-semester manual export), or
    a balance that drops more than the rows explain (catches a cut window in between). Plan pace
    counts up to when the newest PDF was printed, not when it's uploaded.
    """
    per_pdf = [rows_from_pdf(pdf) for pdf in pdfs]
    rows = merge_rows(per_pdf)
    printed = [d for d in map(printed_date, pdfs) if d]
    history = account_history(rows)
    result = build_wrapped(clean(rows), today=max(printed, default=None), history=history)
    maybe_cut_off = any(transaction_count(r) >= GET_SMALLEST_LIMIT for r in per_pdf) or bool(balance_gaps(history))
    return result, maybe_cut_off


def name_on(pdfs):
    """First name for the stats card, from the first PDF that has one. It's only for show, so a
    PDF it can't read leaves the name off instead of failing the request."""
    try:
        return next(filter(None, map(first_name, pdfs)), None)
    except Exception:
        app.logger.exception("Couldn't read the name from an upload")
        return None


def render_wrapped(result, maybe_cut_off=False, name=None):
    return render_template(
        "wrapped.html", w=result, maybe_cut_off=maybe_cut_off, wheel=wheel_cards(result.personalities), count_path="/wrapped", name=name,
    )


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
    pdfs = [p.read_bytes() for p in sorted(run_dir.glob("*.pdf"))]
    return render_wrapped(*build_from_pdfs(pdfs), name_on(pdfs))


@app.errorhandler(413)
def too_large(_):
    return render_home(f"That upload is over {MAX_UPLOAD_MB} MB. A semester of history should be much smaller.", 413, "/error")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Serving on port {port} (http://localhost:{port})", flush=True)
    serve(app, port=port, **SERVE_OPTIONS)

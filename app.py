import os
from pathlib import Path
from urllib.parse import quote

from flask import Flask, render_template, request
from waitress import serve

from wrapped import ParseError, build_wrapped, parse_pdfs

GET_ORIGIN = "https://get.cbord.com"
MAX_UPLOAD_MB = 25
BOOKMARKLET_SOURCE = Path(__file__).parent / "static" / "scripts" / "bookmarklet.js"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


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


@app.post("/wrapped")
def wrapped():
    files = [f for f in request.files.getlist("pdfs") if f.filename]
    if not files:
        return render_home("Choose your transaction history PDF first.", 400)
    try:
        result = build_wrapped(parse_pdfs(f.read() for f in files))
    except ParseError as e:
        return render_home(str(e), 400)
    vendor_table_html = (
        result.vendors.rename(columns=str.title).rename_axis(None)
        .to_html(classes="data", formatters={"Spent": "${:.2f}".format})
    )
    return render_template("wrapped.html", w=result, vendor_table_html=vendor_table_html)


@app.errorhandler(413)
def too_large(_):
    return render_home(f"That upload is over {MAX_UPLOAD_MB} MB. A semester of history should be much smaller.", 413)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Serving on http://localhost:{port}")
    serve(app, host="0.0.0.0", port=port)

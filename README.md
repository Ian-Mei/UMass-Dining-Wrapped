# UMass Dining Wrapped

Spotify-Wrapped-style recap of a semester of UMass dining: favorite dining hall, meal-period
breakdowns, where your dining dollars went, laundry stats, and a dining "personality".

Not affiliated with UMass or UMass Dining.

## How people get their data in

Nobody types their NetID or password into this site. There are two ways in:

1. **Bookmarklet.** The home page has a **Dining Wrapped** button to drag to the bookmarks bar.
   The user logs into GET normally, then clicks the bookmark. It runs inside their own GET tab and
   opens this site's `/import` page, which asks the GET tab (via `postMessage`) for this semester's
   history from `historyPDF.php`, one date window at a time, then submits the PDFs to `/wrapped`.
   GET only returns the newest page of rows (17) per request and silently drops the rest, so
   `/import` checks each window with `/rows` and downloads a full one again in halves.
   Sources: [`static/scripts/bookmarklet.js`](static/scripts/bookmarklet.js) (the fetcher) and
   [`static/scripts/history_windows.js`](static/scripts/history_windows.js) (which windows).
2. **Upload.** GET → View All Transaction History → **Export PDF**, then upload it on the home page.

PDFs are parsed in memory and never written to disk.

## Layout

```
app.py                  Flask routes: / (home), /import (bookmarklet landing), /rows, /wrapped (results)
wrapped/
  transactions.py       PDF bytes → clean DataFrame of charges (PyMuPDF table extraction)
  stats.py              charges → Wrapped (dining halls, vendors, laundry, totals)
  personality.py        personality rules
  __main__.py           python -m wrapped history.pdf  (print stats for a local PDF)
templates/              home.html, import.html, wrapped.html
static/                 CSS, images, loading screen, bookmarklet source
tests/                  pytest suite (synthetic PDFs only, no real data)
```

## Running it

```sh
pip install -r requirements-dev.txt
python app.py                         # serves http://localhost:8000 with waitress
flask --app app run --debug           # or the Flask dev server with auto-reload
python -m pytest                      # tests
node --test tests/                    # bookmarklet date-window tests
python -m wrapped path/to/history.pdf # check what the parser makes of a real export
```

To debug a run, set `WRAPPED_SAVE_UPLOADS` to a folder (e.g. `debug_uploads`). Every upload is then
saved there before parsing, along with `error.txt` if it fails, so you can re-run it with
`python -m wrapped debug_uploads/<run>/*.pdf`. Local use only: it stores people's history.

When deployed behind a proxy, set `WRAPPED_PUBLIC_URL` (e.g. `https://wrapped.example.com`) so the
bookmarklet points at the public address.

## Notes

- Only charges count. Deposits, transfers and refunds are dropped.
- Meal-plan accounts report amounts in meals (`-1`) and money accounts in dollars (`-$9.50`). That's
  how swipes are told apart from dining dollars, so new meal plan names work without code changes.
- At Worcester and Frank, register 1 is Grab 'n Go. Late night (9pm–4am) only exists at Worcester and Berk.
- GET drops meal-swipe history once a meal plan ends, so run it during or right after the semester.
- Never commit real history PDFs. `*.pdf` is gitignored.

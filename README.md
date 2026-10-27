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
   The same row limit applies to each exported PDF, so for a whole semester export a few days at a
   time and upload all the PDFs together (or use the bookmarklet).

PDFs are parsed in memory and never written to disk.

## Layout

```
app.py                  Flask routes: / (home), /import (bookmarklet landing), /rows, /wrapped (results)
wrapped/
  transactions.py       PDF bytes → clean DataFrame of charges (PyMuPDF: table grid + words)
  stats.py              charges → Wrapped (dining halls, vendors, laundry, totals)
  highlights.py         plan run-out pace, routine, Blue Wall, Harvest Market, top-ups, streak
                        calendar, dining clock, fun facts, explorer data
  personality.py        personality rules
  __main__.py           python -m wrapped history.pdf  (print stats for a local PDF)
templates/              home.html, import.html, wrapped.html
static/scripts/explorer.js  the Explore your days / Explore your places screens
static/                 CSS, images, loading screen, bookmarklet source
tests/                  pytest suite (synthetic PDFs only, no real data)
```

## Running it

```sh
pip install -r requirements-dev.txt
python app.py                         # serves http://localhost:8000 with waitress
flask --app app run --debug           # or the Flask dev server with auto-reload
python -m pytest                      # tests
node --test tests/                    # bookmarklet date windows + explorer helpers
python -m wrapped path/to/history.pdf # check what the parser makes of a real export
```

In debug mode every upload is saved to `debug_uploads` (or `WRAPPED_SAVE_UPLOADS`, which also works
outside debug mode). Each one is saved there before parsing, along with `error.txt` if it fails, so you can re-run it with
`python -m wrapped debug_uploads/<run>/*.pdf`. Local use only: it stores people's history.

In debug mode (`flask --app app run --debug`), `/dev` lists the saved runs and `/dev/<run>` renders
the results page for one, so you can work on the page without going through GET. These routes
return 404 unless debug mode is on.

Behind a proxy, the app takes https from the proxy's `X-Forwarded-Proto` header and the host from
`Host`, so the bookmarklet points at the public address. It ignores `X-Forwarded-Host`, which anyone
can send. If the proxy changes `Host`, set `WRAPPED_PUBLIC_URL` (e.g. `https://wrapped.example.com`).

## Deploying

`render.yaml` sets the app up on [Render](https://render.com)'s free plan: in the dashboard, New >
Blueprint, pick this repo, and it installs `requirements.txt` at the versions in `constraints.txt` and runs `python app.py` (waitress
on Render's `PORT`). Every push to `main` redeploys. The free plan sleeps after 15 minutes without
visits, so the first visit after that takes a little while to load. Don't set `WRAPPED_SAVE_UPLOADS`
there: uploads should stay in memory.

Visits are counted with [GoatCounter](https://www.goatcounter.com) (no cookies) when
`WRAPPED_GOATCOUNTER_URL` is set, which only `render.yaml` does. Pages count as `/` (home),
`/wrapped` (a Wrapped made; refreshing the results counts again) and `/error` (a failed upload).
count.js sends that path, the page title ("UMass Dining Wrapped"), the referrer and screen size,
nothing from the page's content. It's pinned to a version with an integrity hash; to upgrade, take
the new hash from [GoatCounter's list](https://www.goatcounter.com/help/countjs-versions).

## Notes

- Only charges count. Deposits, transfers and refunds are dropped.
- Meal-plan accounts report amounts in meals (`-1`) and money accounts in dollars (`-$9.50`). That's
  how swipes are told apart from dining dollars, so new meal plan names work without code changes.
- At Worcester and Frank, register 1 is Grab 'n Go. Late night (9pm–4am) only exists at Worcester and Berk.
- GET drops meal-swipe history once a meal plan ends, so run it during or right after the semester.
- Never commit real history PDFs. `*.pdf` is gitignored.

# UMass Dining Wrapped

Spotify-Wrapped-style recap of a semester of UMass dining, built from GET (get.cbord.com)
transaction-history PDFs. Flask app; the results page is a stack of full-screen "screens".
README.md covers setup, layout and the two ways data gets in (bookmarklet and manual upload).

## Commands

```sh
python -m pytest                       # Python tests (synthetic PDFs from tests/conftest.py)
node --test tests/                     # JS tests: history_windows.js, explorer.js helpers
flask --app app run --debug            # dev server; saves every upload to debug_uploads/
python -m wrapped path/to/history.pdf  # print stats for local PDFs
```

In debug mode, `/dev` lists saved runs and `/dev/<run>` re-renders one (404 outside debug mode).
That's the fastest way to check a change against real data. On Windows use `.venv/Scripts/python.exe`.

## Privacy (hard rules)

- `debug_uploads/` holds friends' real transaction history. Never commit it, any `*.pdf`, or
  `.superpowers/` (all gitignored). Don't put friends' names or their data in commits, PR text or
  tests: write tests with synthetic rows that mimic the real shapes (round times, made-up
  balances, not a real row's exact values). When reporting on saved runs in PRs, use counts
  ("two saved runs"), not names. GitHub keeps every version of a PR description, so get it right
  the first time.
- Uploads are parsed in memory. Nothing is stored server-side except in debug mode or with
  `WRAPPED_SAVE_UPLOADS`. The explorer screens get their data as JSON inside the page, nothing new
  on the server. Keep it that way.

## Where things live

- `wrapped/transactions.py`: PDF bytes → rows → `clean()` frame (one row per charge). Also the GET
  facts: row limits, `balance_gaps`, `account_history`, top-up detection, `printed_date`.
- `wrapped/stats.py`: swipe table, vendor table (Top Spots), laundry, `build_wrapped`.
- `wrapped/highlights.py`: everything newer: plan run-out projection, routine, streak calendar,
  clock, fun facts, Blue Wall, Harvest Market, top-ups, explorer data, raw-data sections.
- `wrapped/personality.py`: personality rules (first match wins).
- `templates/wrapped.html` + `static/styles/wrapped.css`: the results screens.
- `static/scripts/explorer.js`: Explore your days / places. `history_windows.js`: download windows.
  `bookmarklet.js`: runs on GET, only fetches what `/import` asks for (see "Bookmarklet" below).

## GET's PDFs: things learned the hard way

- **Words are drawn separately.** PyMuPDF's `table.extract()` glues them (`08/20/2602:09:40PM`).
  Rows are rebuilt from the drawn grid (`grid_edges`) plus word positions. `find_tables()` was
  ~1s/page; don't go back to it.
- **GET silently returns only the newest N rows per request.** N varies by person (14, 17 and 21
  seen). So history is downloaded in 5-day windows; a window with ≥10 rows (`MAYBE_CUT_OFF_ROWS`)
  is fetched again in halves. The results page warns when a PDF has ≥14 rows
  (`GET_SMALLEST_LIMIT`) or `balance_gaps` finds a balance drop the rows don't explain.
- **Date windows:** `dateS` is included, `dateE` isn't, and GET draws the day line around 8pm
  Eastern (UTC). Windows are back to back, so nothing falls between them.
- **Terminal names:** old style `HampDC3` (number = register; register 1 at Worcester/Frank is
  Grab 'n Go), Fall 2026 style `CPOS Worcester DC` / `CPOS Worcester GG`. Both are handled.
  Grab 'n Go only gets its own count at Worcester and Frank (`GRAB_N_GO_HALLS`).
- **A row can take 2 swipes** (`-2`, e.g. paying for a friend). Count swipes by adding up `amount`,
  never by counting rows. Visits (calendar, clock, streak, routine) count rows.
- **Top-ups:** dining dollars at a vendor within 60s of a meal swipe there (`is_top_up`). They're
  part of the swipe, so not a separate visit and not in Top Spots, but they count in dollars spent.
- **Identical rows:** the same row in two PDFs is one transaction (overlap); identical rows in one
  PDF are separate purchases (unlimited plans' balance never changes). See `merge_rows`.
- **Same-second rows** come in any order (e.g. the Meal Plan Office's `+0` next to a deposit);
  `chain_order` picks the order where balances add up.
- **Silent reloads:** Free Friday and staff accounts get refilled with no row, so a balance going
  *up* unexplained is normal. Only unexplained drops mean missing rows.
- Text sometimes arrives as UTF-8 read as Latin-1 (`CafÃ©`); `display_name` fixes it and strips `CPOS `.
- `clean()` strips digits from `place` (they're register numbers), so in tests "Cafe 1" and
  "Cafe 2" are the same place. Use letters to make distinct ones.
- **`-0` swipes:** unlimited plans sometimes record a swipe of 0 meals with the balance unchanged
  (seen at dinner in the first week). It's still a visit; the explorer tags it `free`.
- **Unreadable amounts** (`-`, `-$`) become 1 swipe or $0 once, in `clean()`. Don't fill them
  again further down.
- An upload with no food at all (only laundry) must still render; watch dtypes on empty frames.

## Dining rules the app encodes

- Dining halls: Hamp, Worcester, Berk, Frank. Late night only at Worcester and Berk. Anything
  before 4am counts as the night before.
- **Blue Wall** = Tavola, Tamales, Wasabi, Star Ginger, Green Fields, Deli Delish, Yum! Bakery,
  People's Organic Coffee, Paciugo. Harvest Market and Peet's are *not* Blue Wall (Harvest has its
  own card from 5 swipes).
- **Plans (YCMP etc.):** "Will you make it to finals?" projects each meal plan, and all
  dining-dollar accounts combined (RAs have an RA account GET spends first plus an untouched
  regular one), to the end of the semester (`SEMESTER_ENDS`: Dec 18 / May 15). Pace counts up to
  the PDF's "Printed:" date, so quiet days slow it down. "What's left" is the balance on that date,
  from `account_history` (which sees accounts `clean()` drops).
- RA training swipes count as normal meals.
- Dining dollars paid at a dining hall are money spent, not swipes.
- **Plan type comes from the account name.** "YCMP" (any case) or "Unlimited" in the account they
  swiped with most. YCMP names usually end in the semester's meal count (`T YCMP Commuter 155`,
  `G YCMP Cmmtr 65`); some don't (`K YCMP Gold`). Other plans exist too (`C Basic Plan`, RA
  training, `Free Friday DC`).
- **Explore your places:** YCMP plans see swipes and dining dollars. Other plans don't choose
  where a swipe goes, so they only see dining dollars, without top-ups, so each place matches its
  Top Spots row. With nothing to list, the screen is left out, and links only point at places it lists.
- **"All your data" tables:** meal columns count visits, not swipes (a note under the tables says
  so). A blank cell means the hall doesn't serve that meal; a dash means zero.

## Personalities

- Rules and thresholds live in `wrapped/personality.py`. Everyone gets every personality they match
  (`Wrapped.personalities`); the first match is their main one, and Average Joe only when none match.
  The results page shows them on a spinning wheel (`static/scripts/personality-wheel.js`); the per-person numbers
  they use (`places_tried`, `meal_plan`, `meals_per_week`, `plan_meals_per_week`) are worked out in `stats.py`.
- The user writes the blurbs in their own casual voice. Use their wording exactly; if a
  placeholder is needed, say it's one.
- Pictures: `static/styles/imgs/personalities/<image>.png`, 400x600 on white. The user draws them; to crop a
  drawing out of their PDF, redraw its vector paths with PyMuPDF on a blank page, leaving out the
  1x1 grid dots and the label, and render it centered (Pillow isn't installed). Renaming a
  personality means renaming its picture too (`git mv`).
- The saved runs are partial semesters (about Aug to Oct, at most ~120 swipes), so whole-semester
  thresholds rarely fire on them. Still run new rules over them and report how many match.

## Results page conventions

- Every screen must fit in one window (phones down to 360x640, laptops down to 1280x540): the
  page uses scroll-snap, and a screen taller than the window breaks moving to the next one. Lists
  scroll inside their card. Each card ends with the "UMass Dining Wrapped · Fall 26" stamp so a
  screenshot stands alone.
- Don't add links that jump ahead to a later screen in a way that skips content (the user removed
  "See this day" for that reason). Place links ("See every visit") into Explore your places are fine.
- After UI changes, check in a real browser (Playwright against `/dev/<run>`) at several sizes, not
  just the tests: measure section heights vs. window height and look for sideways scrolling.

## Bookmarklet

`static/scripts/bookmarklet.js` is inlined into a `javascript:` link by `app.py`: only full-line
comments, and every statement ends with a semicolon. It only fetches the date windows `/import`
asks for and acknowledges each one, so download logic can change without users re-adding the
bookmark. Changing the bookmarklet itself means everyone has to drag it again; avoid that if possible.

## How the user likes to work

- One branch per change off an up-to-date `main`; open a PR, run `/code-review high`, fix what's
  worth fixing, then merge with a merge commit. Branch names should describe the change (rename if
  the scope grows).
- Test first (failing test, then the fix). When a test's expected value changes, say why.
- Before committing or pushing, make sure nothing personal is in the diff.
- No Claude attribution anywhere in git or GitHub (also in the user's global CLAUDE.md).
- Claude Code's permission check blocks `gh pr merge`; ask the user to run
  `! gh pr merge <n> --merge`, then switch to `main` and pull.
- Keep the PR description up to date as commits are added (what changed, test counts).
- For new features, ask what they want first (they like mockups for anything visual), and
  give a recommendation instead of a list of options.

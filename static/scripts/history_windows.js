// Which date windows to download from GET's historyPDF.php. Used by templates/import.html,
// and tested with `node --test tests/` (tests/history_windows.test.js).
//
// GET only returns the newest page of rows for a request (17 when we checked) and drops the rest
// without saying so, so history is downloaded in short windows, and a window that comes back
// full is downloaded again in halves. dateS is inclusive and dateE is exclusive, so back-to-back
// windows don't overlap.
const HistoryWindows = (() => {
  const WINDOW_DAYS = 5;

  const addDays = (date, days) => {
    const d = new Date(date);
    d.setDate(d.getDate() + days);
    return d;
  };

  // Whole days between two local midnights (rounded so daylight saving doesn't matter).
  const daysBetween = (a, b) => Math.round((b - a) / 86400000);

  // GET's date format: 2026-8-15.
  const fmt = (d) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;

  // The semester `today` falls in (or just finished), up to today.
  const semester = (today) => {
    const year = today.getFullYear();
    const monthDay = (today.getMonth() + 1) * 100 + today.getDate();
    let start;
    let end;
    if (monthDay < 115) {
      start = new Date(year - 1, 7, 15);
      end = new Date(year - 1, 11, 31);
    } else if (monthDay < 815) {
      start = new Date(year, 0, 15);
      end = new Date(year, 4, 31);
    } else {
      start = new Date(year, 7, 15);
      end = new Date(year, 11, 31);
    }
    const midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    return { start, end: end > midnight ? midnight : end };
  };

  // Back-to-back windows covering the semester, through the end of its last day.
  const initial = (today) => {
    const { start, end } = semester(today);
    const windows = [];
    for (let s = start; s <= end; s = addDays(s, WINDOW_DAYS)) {
      windows.push({ start: s, end: addDays(s, WINDOW_DAYS) });
    }
    return windows;
  };

  const canSplit = (w) => daysBetween(w.start, w.end) >= 2;

  const split = (w) => {
    const mid = addDays(w.start, Math.floor(daysBetween(w.start, w.end) / 2));
    return [{ start: w.start, end: mid }, { start: mid, end: w.end }];
  };

  return { semester, initial, canSplit, split, fmt };
})();

if (typeof module !== "undefined") module.exports = HistoryWindows;

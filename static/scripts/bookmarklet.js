// Runs on get.cbord.com inside the user's own logged-in session: opens the Wrapped site's /import
// page and downloads the transaction history PDFs it asks for. /import decides which date windows
// to fetch (static/scripts/history_windows.js), so that logic can change without anyone
// re-adding the bookmark. The user's login never touches our server.
//
// app.py inlines this file into a javascript: link, so only use full-line comments
// and end every statement with a semicolon. The `void` keeps the browser from replacing
// the GET page with the returned promise.
void (async () => {
  const APP = "__APP_ORIGIN__";
  const HISTORY_PDF = "/umass/full/historyPDF.php";
  const RETRIES = 3;
  // Per attempt, so a request GET never answers is retried instead of hanging the import.
  const FETCH_TIMEOUT_MS = 20000;
  const DATE = /^\d{4}-\d{1,2}-\d{1,2}$/;

  if (location.hostname !== "get.cbord.com") {
    alert("Log into GET (get.cbord.com) first, then click this bookmark again.");
    return;
  }

  // Must open synchronously on the click, before any await, or the pop-up gets blocked.
  const app = window.open(APP + "/import", "dining-wrapped");
  if (!app) {
    alert("Your browser blocked the pop-up. Allow pop-ups for get.cbord.com and click the bookmark again.");
    return;
  }
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const fetchPdf = async (url) => {
    for (let attempt = 1; ; attempt++) {
      try {
        const res = await fetch(url, { credentials: "same-origin", signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) });
        const type = res.headers.get("content-type") || "";
        if (res.ok && type.includes("pdf")) return await res.arrayBuffer();
        throw new Error("GET didn't send back a PDF. Are you still logged in?");
      } catch (err) {
        if (attempt >= RETRIES) throw err;
        await sleep(1000 * attempt);
      }
    }
  };

  // Clicking the bookmark again replaces the old listener instead of answering every request twice.
  window.removeEventListener("message", window.diningWrappedListener);
  window.diningWrappedListener = async (event) => {
    if (event.origin !== APP || event.source !== app) return;
    const { type, id, start, end } = event.data || {};
    if (type !== "fetch" || !DATE.test(start) || !DATE.test(end)) return;
    // Lets /import know this bookmark is current and working on it, however long GET takes.
    app.postMessage({ type: "ack", id }, APP);
    try {
      const pdf = await fetchPdf(`${HISTORY_PDF}?dateS=${start}&dateE=${end}`);
      app.postMessage({ type: "pdf", id, pdf }, APP, [pdf]);
    } catch (err) {
      app.postMessage({ type: "error", id, message: "Couldn't download your history from GET: " + (err.message || err) }, APP);
    }
  };
  window.addEventListener("message", window.diningWrappedListener);
})();

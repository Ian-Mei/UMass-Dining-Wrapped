// Runs on get.cbord.com inside the user's own logged-in session: downloads this semester's
// transaction history PDFs and hands them to the Wrapped site's /import page. The user's
// login never touches our server.
//
// app.py inlines this file into a javascript: link, so only use full-line comments
// and end every statement with a semicolon. The `void` keeps the browser from replacing
// the GET page with the returned promise.
void (async () => {
  const APP = "__APP_ORIGIN__";
  const HISTORY_PDF = "/umass/full/historyPDF.php";
  // History is fetched in short overlapping windows in case GET caps rows per PDF;
  // the server drops the duplicate rows from the overlap.
  const WINDOW_DAYS = 5;
  const STEP_DAYS = 4;
  const DELAY_MS = 250;
  const RETRIES = 3;

  if (location.hostname !== "get.cbord.com") {
    alert("Log into GET (get.cbord.com) first, then click this bookmark again.");
    return;
  }

  let markReady;
  const ready = new Promise((resolve) => { markReady = resolve; });
  window.addEventListener("message", (event) => {
    if (event.origin === APP && event.data && event.data.type === "ready") markReady();
  });

  // Must open synchronously on the click, before any await, or the pop-up gets blocked.
  const app = window.open(APP + "/import", "dining-wrapped");
  if (!app) {
    alert("Your browser blocked the pop-up. Allow pop-ups for get.cbord.com and click the bookmark again.");
    return;
  }
  const send = (message, transfer) => ready.then(() => app.postMessage(message, APP, transfer || []));
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const fmt = (d) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;

  const today = new Date();
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
  if (end > today) end = today;

  const windows = [];
  for (let s = new Date(start); s <= end; s.setDate(s.getDate() + STEP_DAYS)) {
    const e = new Date(s);
    e.setDate(e.getDate() + WINDOW_DAYS);
    windows.push([new Date(s), e]);
  }

  const fetchPdf = async (url) => {
    for (let attempt = 1; ; attempt++) {
      try {
        const res = await fetch(url, { credentials: "same-origin" });
        const type = res.headers.get("content-type") || "";
        if (res.ok && type.includes("pdf")) return await res.arrayBuffer();
        throw new Error("GET didn't send back a PDF. Are you still logged in?");
      } catch (err) {
        if (attempt >= RETRIES) throw err;
        await sleep(1000 * attempt);
      }
    }
  };

  const pdfs = [];
  try {
    for (let i = 0; i < windows.length; i++) {
      const [s, e] = windows[i];
      pdfs.push(await fetchPdf(`${HISTORY_PDF}?dateS=${fmt(s)}&dateE=${fmt(e)}`));
      send({ type: "progress", done: i + 1, total: windows.length });
      await sleep(DELAY_MS);
    }
  } catch (err) {
    send({ type: "error", message: "Couldn't download your history from GET: " + (err.message || err) });
    return;
  }
  send({ type: "pdfs", pdfs }, pdfs);
})();

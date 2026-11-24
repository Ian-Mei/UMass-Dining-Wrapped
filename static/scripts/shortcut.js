// The code inside the iPhone Shortcut ("Run JavaScript on Webpage"). It runs in the user's logged-in
// GET tab and shows /import in a small box. /import decides which date windows to download
// (static/scripts/history_windows.js) and this fetches them, so download logic can change without
// anyone reinstalling the Shortcut. The user's login never touches our server.
//
// Apple cuts these scripts off after an unpublished time limit, so it calls completion() right
// away and the download carries on in the page.
(() => {
  const APP = "__APP_ORIGIN__";
  const HISTORY_PDF = "/umass/full/historyPDF.php";
  const RETRIES = 3;
  const FETCH_TIMEOUT_MS = 20000;
  // The free server sleeps when idle and can take most of a minute to wake up.
  const WAKE_TIMEOUT_MS = 90000;
  const DATE = /^\d{4}-\d{1,2}-\d{1,2}$/;

  if (window.diningWrappedStop) window.diningWrappedStop();

  const running = new AbortController();
  let frame = null;
  let started = false;
  let wake;

  const box = document.createElement("div");
  box.id = "dining-wrapped";
  box.style.cssText = "position:fixed;left:12px;right:12px;top:12px;z-index:2147483647;overflow:hidden;border-radius:12px;background:#1b1236;color:#fff;font:16px/1.4 -apple-system,sans-serif";
  const notice = document.createElement("div");
  notice.style.cssText = "padding:16px 48px 16px 16px";
  const close = document.createElement("button");
  close.type = "button";
  close.textContent = "×";
  close.setAttribute("aria-label", "Close");
  close.style.cssText = "position:absolute;right:4px;top:4px;width:44px;height:44px;border:0;background:none;color:#fff;font-size:24px";
  close.addEventListener("click", () => stop());
  box.append(notice, close);

  function finishDownloading() {
    clearTimeout(wake);
    running.abort();
    window.removeEventListener("message", onMessage);
  }

  function stop() {
    finishDownloading();
    window.removeEventListener("pageshow", onPageShow);
    window.diningWrappedStop = null;
    box.remove();
  }

  // Back from the results, Safari can restore this page with the old box still on it.
  function onPageShow(event) {
    if (event.persisted) stop();
  }

  function fail(text) {
    finishDownloading();
    if (frame) frame.remove();
    notice.textContent = text;
    box.append(notice);
  }

  const showOnly = (text) => {
    notice.textContent = text;
    document.documentElement.append(box);
    window.diningWrappedStop = stop;
    completion();
  };

  if (location.hostname !== "get.cbord.com") {
    showOnly("Open GET in Safari and log in, then run this from the Share menu.");
    return;
  }
  try {
    new DataTransfer();
  } catch (err) {
    showOnly("This needs a newer iPhone update. Update iOS, or do this part on a laptop.");
    return;
  }

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const fetchPdf = async (url) => {
    for (let attempt = 1; ; attempt++) {
      const timeout = new AbortController();
      const abort = () => timeout.abort();
      const timer = setTimeout(abort, FETCH_TIMEOUT_MS);
      running.signal.addEventListener("abort", abort);
      try {
        const res = await fetch(url, { credentials: "same-origin", signal: timeout.signal });
        const type = res.headers.get("content-type") || "";
        if (res.ok && type.includes("pdf")) return await res.arrayBuffer();
        throw new Error("GET didn't send back a PDF. Are you still logged in?");
      } catch (err) {
        if (attempt >= RETRIES || running.signal.aborted) throw err;
        await sleep(1000 * attempt);
      } finally {
        clearTimeout(timer);
        running.signal.removeEventListener("abort", abort);
      }
    }
  };

  // A normal form post, so the Wrapped opens in this tab and the server needs no cross-site access.
  const openWrapped = (pdfs) => {
    const form = document.createElement("form");
    form.action = APP + "/wrapped";
    form.method = "post";
    form.enctype = "multipart/form-data";
    form.style.display = "none";
    const input = document.createElement("input");
    input.type = "file";
    input.name = "pdfs";
    input.multiple = true;
    const files = new DataTransfer();
    pdfs.forEach((pdf, i) => files.items.add(new File([pdf], "history-" + i + ".pdf", { type: "application/pdf" })));
    input.files = files.files;
    form.append(input);
    document.documentElement.append(form);
    form.submit();
  };

  // The box may already be closed by the time a download finishes.
  const reply = (message, transfer) => {
    if (frame.contentWindow) frame.contentWindow.postMessage(message, APP, transfer || []);
  };

  async function onMessage(event) {
    if (event.origin !== APP || event.source !== frame.contentWindow) return;
    if (!started) {
      started = true;
      clearTimeout(wake);
      notice.remove();
      frame.style.position = "static";
      frame.style.visibility = "visible";
    }
    const { type, id, start, end, pdfs } = event.data || {};
    if (type === "done") {
      try {
        if (!Array.isArray(pdfs) || !pdfs.length) throw new Error("no PDFs");
        openWrapped(pdfs);
      } catch (err) {
        fail("Couldn't open your Wrapped. Run the Shortcut again.");
      }
      return;
    }
    if (type !== "fetch" || !DATE.test(start) || !DATE.test(end)) return;
    reply({ type: "ack", id });
    try {
      const pdf = await fetchPdf(HISTORY_PDF + "?dateS=" + start + "&dateE=" + end);
      reply({ type: "pdf", id, pdf }, [pdf]);
    } catch (err) {
      if (!running.signal.aborted) reply({ type: "error", id, message: "Couldn't download your history from GET: " + (err.message || err) });
    }
  }

  notice.textContent = "Starting Dining Wrapped… this can take up to a minute.";
  frame = document.createElement("iframe");
  frame.src = APP + "/import";
  frame.title = "Dining Wrapped download progress";
  frame.style.cssText = "display:block;position:absolute;left:0;top:0;width:100%;height:132px;border:0;visibility:hidden";
  box.append(frame);
  wake = setTimeout(() => fail("Dining Wrapped didn't start. Check your connection and run the Shortcut again."), WAKE_TIMEOUT_MS);
  window.addEventListener("message", onMessage);
  window.addEventListener("pageshow", onPageShow);
  window.diningWrappedStop = stop;
  document.documentElement.append(box);
  completion();
})();

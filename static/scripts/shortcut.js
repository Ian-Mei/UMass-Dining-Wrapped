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
  const DATE = /^\d{4}-\d{1,2}-\d{1,2}$/;

  const old = document.getElementById("dining-wrapped");
  if (old) old.remove();
  window.removeEventListener("message", window.diningWrappedListener);

  const box = document.createElement("div");
  box.id = "dining-wrapped";
  box.style.cssText = "position:fixed;left:12px;right:12px;top:12px;z-index:2147483647;overflow:hidden;border-radius:12px;background:#1b1236;color:#fff;font:16px/1.4 -apple-system,sans-serif";

  if (location.hostname !== "get.cbord.com") {
    box.style.padding = "16px";
    box.textContent = "Open GET in Safari and log in, then run this from the Share menu.";
    document.documentElement.append(box);
    completion();
    return;
  }

  const frame = document.createElement("iframe");
  frame.src = APP + "/import";
  frame.title = "Dining Wrapped download progress";
  frame.style.cssText = "display:block;width:100%;height:104px;border:0";

  const close = document.createElement("button");
  close.type = "button";
  close.textContent = "\u00d7";
  close.setAttribute("aria-label", "Close");
  close.style.cssText = "position:absolute;right:4px;top:4px;width:44px;height:44px;border:0;background:none;color:#fff;font-size:24px";
  close.addEventListener("click", () => {
    window.removeEventListener("message", window.diningWrappedListener);
    box.remove();
  });
  box.append(frame, close);

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const fetchPdf = async (url) => {
    for (let attempt = 1; ; attempt++) {
      const timeout = new AbortController();
      const timer = setTimeout(() => timeout.abort(), FETCH_TIMEOUT_MS);
      try {
        const res = await fetch(url, { credentials: "same-origin", signal: timeout.signal });
        const type = res.headers.get("content-type") || "";
        if (res.ok && type.includes("pdf")) return await res.arrayBuffer();
        throw new Error("GET didn't send back a PDF. Are you still logged in?");
      } catch (err) {
        if (attempt >= RETRIES) throw err;
        await sleep(1000 * attempt);
      } finally {
        clearTimeout(timer);
      }
    }
  };

  // A normal form post, so the Wrapped opens in this tab and the server needs no cross-site access.
  const openWrapped = (pdfs) => {
    if (!Array.isArray(pdfs) || !pdfs.length) return;
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

  window.diningWrappedListener = async (event) => {
    if (event.origin !== APP || event.source !== frame.contentWindow) return;
    const { type, id, start, end, pdfs } = event.data || {};
    if (type === "done") {
      openWrapped(pdfs);
      return;
    }
    if (type !== "fetch" || !DATE.test(start) || !DATE.test(end)) return;
    frame.contentWindow.postMessage({ type: "ack", id }, APP);
    try {
      const pdf = await fetchPdf(HISTORY_PDF + "?dateS=" + start + "&dateE=" + end);
      frame.contentWindow.postMessage({ type: "pdf", id, pdf }, APP, [pdf]);
    } catch (err) {
      frame.contentWindow.postMessage({ type: "error", id, message: "Couldn't download your history from GET: " + (err.message || err) }, APP);
    }
  };
  window.addEventListener("message", window.diningWrappedListener);
  document.documentElement.append(box);
  completion();
})();

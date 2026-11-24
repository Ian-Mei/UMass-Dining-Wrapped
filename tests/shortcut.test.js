const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const APP = "https://wrapped.example";
const code = fs.readFileSync(path.join(__dirname, "..", "static", "scripts", "shortcut.js"), "utf8").replace("__APP_ORIGIN__", APP);

const element = (tag) => ({
  tag, style: {}, children: [], on: {}, append(...kids) { this.children.push(...kids); },
  addEventListener(type, fn) { this.on[type] = fn; }, setAttribute() {},
  remove() { this.removed = true; if (tag === "iframe") this.contentWindow = null; }, submit() { this.submitted = true; },
});

// Runs the script on a pretend page and hands back what it did.
const run = (hostname, fetchPdf, overrides = {}) => {
  const made = [];
  const sent = [];
  const listeners = { message: [], pageshow: [] };
  const timers = [];
  let completed = 0;
  const root = element("html");
  const sandbox = {
    location: { hostname },
    setTimeout: (fn, ms) => { const t = setTimeout(fn, ms); t.unref(); timers.push({ fn, ms }); return t; },
    clearTimeout, AbortController,
    completion: () => { completed += 1; },
    fetch: fetchPdf,
    File: class { constructor(parts, name) { this.parts = parts; this.name = name; } },
    DataTransfer: class { constructor() { const list = []; this.files = list; this.items = { add: (f) => list.push(f) }; } },
    document: {
      documentElement: root,
      getElementById: () => null,
      createElement: (tag) => {
        const e = element(tag);
        if (tag === "iframe") e.contentWindow = { postMessage: (message) => sent.push(message) };
        made.push(e);
        return e;
      },
    },
    addEventListener: (type, fn) => listeners[type].push(fn),
    removeEventListener: (type, fn) => { listeners[type] = listeners[type].filter((f) => f !== fn); },
    ...overrides,
  };
  sandbox.window = sandbox;
  vm.runInNewContext(code, sandbox);
  const frame = made.find((e) => e.tag === "iframe");
  const say = (data, origin = APP, source = frame && frame.contentWindow) => Promise.all(listeners.message.map((fn) => fn({ origin, source, data })));
  const box = made[0];
  const notice = made[1];
  return { made, sent, frame, say, box, notice, timers, listeners, sandbox, completed: () => completed };
};

const pdfResponse = () => ({
  ok: true,
  headers: { get: () => "application/pdf" },
  arrayBuffer: async () => new ArrayBuffer(4),
});

test("away from GET it says so and opens nothing", () => {
  const page = run("example.com");
  assert.strictEqual(page.frame, undefined);
  assert.strictEqual(page.completed(), 1);
  assert.match(page.notice.textContent, /log in/);
  assert.ok(page.made.some((e) => e.tag === "button"), "it can be closed");
});

test("on GET it opens the import box and finishes the Shortcut right away", () => {
  const page = run("get.cbord.com");
  assert.strictEqual(page.frame.src, APP + "/import");
  assert.strictEqual(page.completed(), 1);
});

test("it downloads a window the import box asks for", async () => {
  const urls = [];
  const page = run("get.cbord.com", async (url) => { urls.push(url); return pdfResponse(); });
  await page.say({ type: "fetch", id: 3, start: "2026-8-15", end: "2026-8-20" });
  assert.deepStrictEqual(urls, ["/umass/full/historyPDF.php?dateS=2026-8-15&dateE=2026-8-20"]);
  assert.deepStrictEqual(page.sent.map((m) => m.type), ["ack", "pdf"]);
  assert.strictEqual(page.sent[1].id, 3);
});

test("it ignores messages from anywhere else", async () => {
  let fetched = 0;
  const page = run("get.cbord.com", async () => { fetched += 1; return pdfResponse(); });
  const request = { type: "fetch", id: 1, start: "2026-8-15", end: "2026-8-20" };
  await page.say(request, "https://evil.example");
  await page.say(request, APP, {});
  await page.say({ ...request, start: "../../secret" });
  assert.strictEqual(fetched, 0);
});

test("when it's done it posts the PDFs to the site in this tab", async () => {
  const page = run("get.cbord.com");
  await page.say({ type: "done", pdfs: [new ArrayBuffer(4), new ArrayBuffer(4)] });
  const form = page.made.find((e) => e.tag === "form");
  assert.strictEqual(form.action, APP + "/wrapped");
  assert.strictEqual(form.method, "post");
  assert.strictEqual(form.enctype, "multipart/form-data");
  assert.strictEqual(form.submitted, true);
  const input = page.made.find((e) => e.tag === "input");
  assert.strictEqual(input.name, "pdfs");
  assert.strictEqual(input.files.length, 2);
});

test("it says it's starting until the site answers", async () => {
  const page = run("get.cbord.com", async () => pdfResponse());
  assert.match(page.notice.textContent, /Starting/);
  await page.say({ type: "fetch", id: 1, start: "2026-8-15", end: "2026-8-20" });
  assert.strictEqual(page.notice.removed, true);
  assert.strictEqual(page.frame.style.visibility, "visible");
});

test("it says so if the site never wakes up", () => {
  const page = run("get.cbord.com");
  page.timers.find((t) => t.ms === 90000).fn();
  assert.strictEqual(page.frame.removed, true);
  assert.match(page.notice.textContent, /run the Shortcut again/);
});

test("an iPhone too old to upload is told before it downloads anything", () => {
  const page = run("get.cbord.com", undefined, { DataTransfer: class { constructor() { throw new TypeError("nope"); } } });
  assert.strictEqual(page.frame, undefined);
  assert.match(page.notice.textContent, /update/i);
  assert.strictEqual(page.completed(), 1);
});

test("a failed upload shows an error instead of hanging", async () => {
  const page = run("get.cbord.com", undefined, { File: class { constructor() { throw new Error("no file"); } } });
  await page.say({ type: "done", pdfs: [new ArrayBuffer(4)] });
  assert.match(page.notice.textContent, /Run the Shortcut again/);
  assert.strictEqual(page.frame.removed, true);
});

test("closing mid-download stops it without an error", async () => {
  let release;
  let signal;
  const page = run("get.cbord.com", (url, options) => { signal = options.signal; return new Promise((resolve) => { release = resolve; }); });
  const pending = page.say({ type: "fetch", id: 1, start: "2026-8-15", end: "2026-8-20" });
  page.made.find((e) => e.tag === "button").on.click();
  assert.strictEqual(signal.aborted, true);
  assert.strictEqual(page.box.removed, true);
  page.frame.contentWindow = null;
  release(pdfResponse());
  await pending;
  assert.strictEqual(page.listeners.message.length, 0);
});

test("coming back to GET from the results clears the old box", () => {
  const page = run("get.cbord.com");
  page.listeners.pageshow[0]({ persisted: false });
  assert.notStrictEqual(page.box.removed, true);
  page.listeners.pageshow[0]({ persisted: true });
  assert.strictEqual(page.box.removed, true);
});

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const APP = "https://wrapped.example";
const code = fs.readFileSync(path.join(__dirname, "..", "static", "scripts", "shortcut.js"), "utf8").replace("__APP_ORIGIN__", APP);

const element = (tag) => ({
  tag, style: {}, children: [], append(...kids) { this.children.push(...kids); },
  addEventListener() {}, setAttribute() {}, remove() { this.removed = true; }, submit() { this.submitted = true; },
});

// Runs the script on a pretend page and hands back what it did.
const run = (hostname, fetchPdf) => {
  const made = [];
  const sent = [];
  const listeners = [];
  let completed = 0;
  const root = element("html");
  const sandbox = {
    location: { hostname },
    setTimeout, clearTimeout, AbortController,
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
    addEventListener: (type, fn) => listeners.push(fn),
    removeEventListener() {},
  };
  sandbox.window = sandbox;
  vm.runInNewContext(code, sandbox);
  const frame = made.find((e) => e.tag === "iframe");
  const say = (data, origin = APP, source = frame && frame.contentWindow) => listeners[0]({ origin, source, data });
  return { made, sent, frame, say, completed: () => completed };
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
  assert.match(page.made[0].textContent, /log in/);
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

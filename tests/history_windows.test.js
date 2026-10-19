// Run with: node --test tests/
const test = require("node:test");
const assert = require("node:assert");
const W = require("../static/scripts/history_windows.js");

const span = (w) => `${W.fmt(w.start)}..${W.fmt(w.end)}`;

test("fall semester runs from Aug 15 through today", () => {
  const { start, end } = W.semester(new Date(2026, 9, 19, 14, 30));
  assert.strictEqual(W.fmt(start), "2026-8-15");
  assert.strictEqual(W.fmt(end), "2026-10-19");
});

test("early January still means last fall", () => {
  const { start, end } = W.semester(new Date(2027, 0, 5));
  assert.strictEqual(W.fmt(start), "2026-8-15");
  assert.strictEqual(W.fmt(end), "2026-12-31");
});

test("spring semester", () => {
  const { start, end } = W.semester(new Date(2027, 6, 1));
  assert.strictEqual(W.fmt(start), "2027-1-15");
  assert.strictEqual(W.fmt(end), "2027-5-31");
});

test("initial windows are back to back and include today", () => {
  const windows = W.initial(new Date(2026, 9, 19, 14, 30));
  assert.strictEqual(span(windows[0]), "2026-8-15..2026-8-20");
  assert.strictEqual(span(windows[1]), "2026-8-20..2026-8-25");
  for (let i = 1; i < windows.length; i++) {
    assert.strictEqual(windows[i].start.getTime(), windows[i - 1].end.getTime());
  }
  const last = windows[windows.length - 1];
  assert.ok(last.start <= new Date(2026, 9, 19) && last.end > new Date(2026, 9, 19));
  assert.strictEqual(windows.length, 14);
});

test("split halves a window without overlap", () => {
  const [a, b] = W.split({ start: new Date(2026, 8, 1), end: new Date(2026, 8, 6) });
  assert.strictEqual(span(a), "2026-9-1..2026-9-3");
  assert.strictEqual(span(b), "2026-9-3..2026-9-6");
});

test("splitting stops at one day", () => {
  const two = { start: new Date(2026, 8, 1), end: new Date(2026, 8, 3) };
  assert.ok(W.canSplit(two));
  const [a, b] = W.split(two);
  assert.strictEqual(span(a), "2026-9-1..2026-9-2");
  assert.strictEqual(span(b), "2026-9-2..2026-9-3");
  assert.ok(!W.canSplit(a));
});

test("split works across the daylight saving change", () => {
  const [a, b] = W.split({ start: new Date(2026, 10, 1), end: new Date(2026, 10, 6) });
  assert.strictEqual(span(a), "2026-11-1..2026-11-3");
  assert.strictEqual(span(b), "2026-11-3..2026-11-6");
});

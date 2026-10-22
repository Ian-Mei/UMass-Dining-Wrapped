// Run with: node --test tests/
const test = require("node:test");
const assert = require("node:assert");
const X = require("../static/scripts/explorer.js");

const p = (day, swipes, dollars = 0, top_up = false) => ({ day, time: "12:00 PM", place: "Tamales", swipes, dollars, top_up });

test("a month as weeks starting on Sunday", () => {
  const cells = X.monthCells(2026, 8); // September 2026 starts on a Tuesday
  assert.deepStrictEqual(cells.slice(0, 3), [null, null, "2026-09-01"]);
  assert.strictEqual(cells.length % 7, 0);
  assert.strictEqual(cells.filter(Boolean).length, 30);
  assert.strictEqual(cells.filter(Boolean).at(-1), "2026-09-30");
});

test("visits per day leave top-ups out", () => {
  const visits = X.visitsByDay([p("2026-09-14", 1), p("2026-09-14", 0, 3, true), p("2026-09-15", 2)]);
  assert.deepStrictEqual(visits, { "2026-09-14": 1, "2026-09-15": 1 });
  assert.strictEqual(X.level(7), 4);
  assert.strictEqual(X.level(undefined), 0);
});

test("tags and totals", () => {
  assert.strictEqual(X.tag(p("2026-09-14", 1)), "1 swipe");
  assert.strictEqual(X.tag(p("2026-09-14", 2)), "2 swipes");
  assert.strictEqual(X.tag(p("2026-09-14", 0, 3)), "$3.00");
  assert.strictEqual(X.tag(p("2026-09-14", 0, 0)), "free");
  assert.strictEqual(X.totals([p("d", 1), p("d", 2), p("d", 0, 3)]), "3 swipes · $3.00");
  assert.strictEqual(X.totals([p("d", 0, 4.5)]), "$4.50");
  assert.strictEqual(X.totals([]), "");
});

test("day labels use the local date", () => {
  assert.strictEqual(X.dayLabel("2026-09-14"), "Mon, Sep 14");
});

test("grouping keeps days in order", () => {
  const groups = X.groupByDay([p("2026-09-14", 1), p("2026-09-14", 1), p("2026-09-15", 1)]);
  assert.deepStrictEqual([...groups.keys()], ["2026-09-14", "2026-09-15"]);
  assert.strictEqual(groups.get("2026-09-14").length, 2);
});

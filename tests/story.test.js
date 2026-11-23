// Run with: node --test tests/*.test.js
const test = require("node:test");
const assert = require("node:assert");
const S = require("../static/scripts/story.js");
const C = require("../static/scripts/share-card.js");

test("arrow keys, space and page keys move one screen", () => {
  for (const key of ["ArrowRight", "ArrowDown", "PageDown", " "]) assert.strictEqual(S.keyStep(key), 1);
  for (const key of ["ArrowLeft", "ArrowUp", "PageUp"]) assert.strictEqual(S.keyStep(key), -1);
  assert.strictEqual(S.keyStep("a"), 0);
});

test("moving stops at the first and last screen", () => {
  assert.strictEqual(S.targetIndex(3, 1, 10), 4);
  assert.strictEqual(S.targetIndex(0, -1, 10), 0);
  assert.strictEqual(S.targetIndex(9, 1, 10), 9);
});

test("text shrinks only as far as it needs to fit", () => {
  const measure = (text, size) => text.length * size * 0.5;
  assert.strictEqual(C.fitSize(measure, "Joe", 100, 900), 100);
  const size = C.fitSize(measure, "A Very Long Personality Name", 100, 500);
  assert.ok(size < 100 && measure("A Very Long Personality Name", size) <= 500);
});

test("the saved file is named for the semester", () => {
  assert.strictEqual(C.fileName("Fall 26"), "umass-dining-wrapped-fall-26.png");
});

test("art is clear of a block only with a gap around it", () => {
  const art = { left: 0, top: 0, right: 100, bottom: 100 };
  assert.strictEqual(S.clearOf(art, [{ left: 120, top: 0, right: 200, bottom: 50 }], 10), true);
  assert.strictEqual(S.clearOf(art, [{ left: 105, top: 0, right: 200, bottom: 50 }], 10), false);
  assert.strictEqual(S.clearOf(art, [], 10), true);
});

test("art takes the largest size that's clear, or none", () => {
  const clearAt = (limit) => (fit) => fit <= limit;
  assert.strictEqual(S.bestFit([1, 0.8, 0.6], clearAt(1)), 1);
  assert.strictEqual(S.bestFit([1, 0.8, 0.6], clearAt(0.7)), 0.6);
  assert.strictEqual(S.bestFit([1, 0.8, 0.6], clearAt(0.5)), null);
});

test("laptops save the card; only phones open the share sheet", () => {
  assert.strictEqual(C.usesShareSheet(true, false), false);
  assert.strictEqual(C.usesShareSheet(true, true), true);
  assert.strictEqual(C.usesShareSheet(false, true), false);
});

test("the background holds each color, then blends to the next", () => {
  const colors = ["#111111", "#222222", "#333333"];
  const tops = [0, 100, 200];
  assert.strictEqual(S.backdropColor(colors, tops, 0), "#111111");
  assert.strictEqual(S.backdropColor(colors, tops, 100), "#222222");
  assert.strictEqual(S.backdropColor(colors, tops, 50), "color-mix(in oklab, #222222 50.0%, #111111)");
  assert.strictEqual(S.backdropColor(colors, tops, 125), "color-mix(in oklab, #333333 15.6%, #222222)");
});

test("scrolling past either end keeps the end color", () => {
  const colors = ["#111111", "#222222"];
  assert.strictEqual(S.backdropColor(colors, [0, 100], -40), "#111111");
  assert.strictEqual(S.backdropColor(colors, [0, 100], 180), "#222222");
});

test("a screen's offset runs from -1 before it arrives to 1 after it's passed", () => {
  assert.strictEqual(S.screenOffset(100, 100, 100), 0);
  assert.strictEqual(S.screenOffset(150, 100, 100), 0.5);
  assert.strictEqual(S.screenOffset(50, 100, 100), -0.5);
  assert.strictEqual(S.screenOffset(900, 100, 100), 1);
  assert.strictEqual(S.screenOffset(-900, 100, 100), -1);
});

test("shift+space goes back, and other shift+keys stay with the browser", () => {
  assert.strictEqual(S.keyStep(" ", true), -1);
  assert.strictEqual(S.keyStep("ArrowDown", true), 0);
  assert.strictEqual(S.keyStep("ArrowLeft", true), 0);
});

test("the keys only stay in a box that really has more to scroll", () => {
  assert.strictEqual(S.canScroll({ scrollHeight: 200, clientHeight: 100, scrollWidth: 50, clientWidth: 50 }), true);
  assert.strictEqual(S.canScroll({ scrollHeight: 100, clientHeight: 100, scrollWidth: 90, clientWidth: 50 }), true);
  assert.strictEqual(S.canScroll({ scrollHeight: 100, clientHeight: 100, scrollWidth: 50, clientWidth: 50 }), false);
});

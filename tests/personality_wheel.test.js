// Run with: node --test tests/
const test = require("node:test");
const assert = require("node:assert");
const W = require("../static/scripts/personality-wheel.js");

test("a full ring for many cards, a short arc for a few", () => {
  assert.strictEqual(W.gapFor(18), 20);
  assert.strictEqual(W.gapFor(3), 30);
  assert.strictEqual(W.gapFor(1), 30);
});

test("neighbouring cards don't overlap", () => {
  for (const n of [1, 3, 19, 20]) {
    const r = W.radiusFor(n, 150);
    const apart = 2 * r * Math.sin(W.gapFor(n) * Math.PI / 360);  // distance between neighbours
    assert.ok(apart >= 150, `${n} cards: ${apart}`);
  }
});

test("shortest turn", () => {
  assert.strictEqual(W.shortest(350), -10);
  assert.strictEqual(W.shortest(-350), 10);
  assert.strictEqual(W.shortest(720 + 90), 90);
  assert.strictEqual(W.shortest(0), 0);
});

test("the card facing front", () => {
  const slots = [0, 120, 240];
  assert.strictEqual(W.frontmost(slots, 0), 0);
  assert.strictEqual(W.frontmost(slots, -120), 1);
  assert.strictEqual(W.frontmost(slots, -1440 - 245), 2);  // after a few turns
});

test("shuffle keeps every card", () => {
  const cards = ["a", "b", "c", "d"];
  assert.deepStrictEqual(W.shuffle(cards, () => 0.5).slice().sort(), cards);
  assert.deepStrictEqual(cards, ["a", "b", "c", "d"]);  // not changed in place
});

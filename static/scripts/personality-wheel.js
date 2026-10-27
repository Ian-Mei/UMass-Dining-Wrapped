// The personality screen: a 3D ring of every personality card floats up spinning, slows down and
// lands on their main personality. If they got more than one, "See what other personalities you
// got" drops the ones they didn't get and lets them turn the wheel through theirs.
// templates/wrapped.html renders the cards (#wheel); it plays once, the first time the screen shows.
// The helpers at the top are tested with `node --test tests/` (tests/personality_wheel.test.js).
const PersonalityWheel = (() => {
  const SPIN_MS = 4200;
  const SPIN_TURNS = 4;
  const SPREAD_MS = 900;
  const TURN_MS = 700;
  const MAX_GAP = 30;  // degrees between cards once it's only theirs, so they sit side by side

  // Degrees between neighbouring cards: a full ring for many, a short arc for a few.
  const gapFor = (n) => Math.min(360 / n, MAX_GAP);
  // How far out the cards sit so neighbours don't overlap.
  const radiusFor = (n, cardWidth) => cardWidth / 2 / Math.tan(gapFor(n) * Math.PI / 360) + cardWidth / 10;
  // An angle as the shortest turn, between -180 and 180.
  const shortest = (degrees) => ((degrees % 360) + 540) % 360 - 180;
  // The slot facing front when the ring is turned to angle.
  const frontmost = (slots, angle) => {
    let best = 0;
    slots.forEach((slot, i) => {
      if (Math.abs(shortest(slot + angle)) < Math.abs(shortest(slots[best] + angle))) best = i;
    });
    return best;
  };
  const shuffle = (items, random = Math.random) => {
    const out = items.slice();
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  };

  const easeOut = (t) => 1 - Math.pow(1 - t, 4);
  const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

  const start = (root) => {
    const owned = JSON.parse(root.dataset.owned);
    const stage = root.querySelector(".wheelstage");
    const ring = root.querySelector(".ring");
    const info = root.querySelector(".wheelinfo");
    const more = root.querySelector(".wheelmore");
    const count = root.querySelector(".wheelcount");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Shuffled so the spin shows them in a different order every time.
    let cards = shuffle([...ring.querySelectorAll(".wheelcard")]).map((el, i, all) => ({
      el, name: el.dataset.name, blurb: el.dataset.blurb, reason: el.dataset.reason, slot: i * 360 / all.length, fade: 1,
    }));
    const cardWidth = () => cards[0].el.offsetWidth;
    let radius = radiusFor(cards.length, cardWidth());
    // ready: their cards are in place and the arrows and dragging can turn the wheel.
    let angle = 0, rise = 0, current = 0, browsing = false, ready = false, frame = null;

    const render = () => {
      // Pushed back by its radius so the front card is exactly its normal size.
      ring.style.transform = `translateY(${rise}px) translateZ(${-radius}px) rotateY(${angle}deg)`;
      const front = frontmost(cards.map((c) => c.slot), angle);
      cards.forEach((c, i) => {
        c.el.style.transform = `rotateY(${c.slot}deg) translateZ(${radius}px) scale(${0.6 + 0.4 * c.fade})`;
        c.el.style.opacity = c.fade;
        c.el.style.visibility = c.fade > 0.01 ? "" : "hidden";
        c.el.classList.toggle("front", i === front && Math.abs(shortest(c.slot + angle)) < 6);
      });
    };

    const animate = (ms, step, done) => {
      cancelAnimationFrame(frame);
      const t0 = performance.now();
      const tick = (now) => {
        const t = Math.min(1, (now - t0) / ms);
        step(t);
        render();
        if (t < 1) frame = requestAnimationFrame(tick);
        else if (done) done();
      };
      frame = requestAnimationFrame(tick);
    };

    const show = (name) => {
      const card = cards.find((c) => c.name === name);
      info.querySelector(".wheeltag").textContent = name === owned[0] ? "Your personality" : "Also you";
      info.querySelector(".wheeltitle").textContent = card.name;
      info.querySelector(".wheelblurb").textContent = card.blurb;
      info.querySelector(".wheelreason").textContent = card.reason;
      if (browsing) count.textContent = `${current + 1} of ${owned.length}`;
      root.classList.add("landed");
      if (more) more.disabled = false;
    };

    const turnTo = (index) => {
      current = (index + owned.length) % owned.length;
      const card = cards.find((c) => c.name === owned[current]);
      const from = angle, by = shortest(-card.slot - angle);
      animate(reduceMotion ? 1 : TURN_MS, (t) => { angle = from + by * easeInOut(t); }, () => show(card.name));
    };

    // Their cards close up into a short arc around the main one; the rest fade away.
    const browse = () => {
      if (browsing || !root.classList.contains("landed")) return;  // not until the spin has landed
      browsing = true;
      root.classList.add("browsing");
      const theirs = owned.map((name) => cards.find((c) => c.name === name));
      const r0 = radius, r1 = radiusFor(theirs.length, cardWidth());
      const from = cards.map((c) => c.slot);
      const goal = new Map(theirs.map((c, i) => [c, i * gapFor(theirs.length) - angle]));
      animate(reduceMotion ? 1 : SPREAD_MS, (t) => {
        const e = easeInOut(t);
        cards.forEach((c, i) => {
          if (goal.has(c)) c.slot = from[i] + shortest(goal.get(c) - from[i]) * e;
          else c.fade = 1 - e;
        });
        radius = r0 + (r1 - r0) * e;
      }, () => {
        cards.filter((c) => !goal.has(c)).forEach((c) => c.el.remove());
        cards = theirs;
        ready = true;
        turnTo(1);
      });
    };

    const spin = () => {
      const main = cards.find((c) => c.name === owned[0]);
      const to = -main.slot - 360 * SPIN_TURNS, from = to + 360 * SPIN_TURNS + Math.random() * 360;
      const depth = stage.offsetHeight;
      root.classList.add("spinning");
      animate(reduceMotion ? 1 : SPIN_MS, (t) => {
        rise = depth * Math.pow(1 - Math.min(1, t * 2.5), 3);  // floats up in the first ~1.7s
        angle = from + (to - from) * easeOut(t);                 // fast, then slows into place
      }, () => show(main.name));
    };

    if (more) {
      more.disabled = true;  // until the spin lands
      more.addEventListener("click", browse);
      root.querySelector(".wheelprev").addEventListener("click", () => ready && turnTo(current - 1));
      root.querySelector(".wheelnext").addEventListener("click", () => ready && turnTo(current + 1));
    }

    // Once browsing, dragging sideways turns the wheel and lets go on the nearest card.
    let dragX = null, dragAngle = 0;
    stage.addEventListener("pointerdown", (event) => {
      if (!ready) return;
      cancelAnimationFrame(frame);
      dragX = event.clientX;
      dragAngle = angle;
      stage.setPointerCapture(event.pointerId);
    });
    stage.addEventListener("pointermove", (event) => {
      if (dragX === null) return;
      angle = dragAngle + (event.clientX - dragX) * 0.4;
      render();
    });
    const letGo = () => {
      if (dragX === null) return;
      dragX = null;
      const front = cards[frontmost(cards.map((c) => c.slot), angle)];
      turnTo(owned.indexOf(front.name));
    };
    stage.addEventListener("pointerup", letGo);
    stage.addEventListener("pointercancel", letGo);

    // Cards are sized by the window's height, so the ring's radius follows it. (Not while their
    // cards are closing up: that animation sets the radius itself.)
    window.addEventListener("resize", () => {
      if (browsing && !ready) return;
      radius = radiusFor(cards.length, cardWidth());
      render();
    });

    // Hidden below until the screen shows, then it plays once.
    rise = stage.offsetHeight;
    render();
    new IntersectionObserver((entries, observer) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      observer.disconnect();
      spin();
    }, { threshold: 0.5 }).observe(root);
  };

  return { gapFor, radiusFor, shortest, frontmost, shuffle, start };
})();

if (typeof module !== "undefined") {
  module.exports = PersonalityWheel;
} else {
  const root = document.getElementById("wheel");
  if (root) {
    root.classList.add("wheel-js");
    PersonalityWheel.start(root);
  }
}

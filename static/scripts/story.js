// Moves through the results page one full screen at a time: keys, clicks, the arrows or scrolling.
const Story = (() => {
  const FORWARD = ["ArrowRight", "ArrowDown", "PageDown", " "];
  const BACK = ["ArrowLeft", "ArrowUp", "PageUp"];
  // Clicking these does their own thing instead of moving to the next screen.
  const INTERACTIVE = "a, button, input, select, textarea, label, .wheelstage, .rawdata, .xmonth, .xday-list, .xvisit-list, .xchips, .heatmap, .story-nav";
  // Up and down scroll these lists when the keyboard is inside them.
  const SCROLLS_ITSELF = ".rawdata, .xday-list, .xvisit-list, .xchips";
  const CLONE_COLORS = ["#afb1ff", "#16d0a6", "#ffe24a", "#fff6e9"];
  // What the art has to stay clear of. Text is measured by its letters, the rest by its box.
  const TEXT = "h1, h2, .big, .caption, .headline, .remark, .notice, .feedback, .explore-link, .stamp, .itemname, .itemvalue";
  const BLOCKS = ".socials, .pitch, .poster, .wheelstage, .wheelinfo, #bluewallchart .statcard, #clock .statcard, #calendar .statcard, #plans .statcard, #tables .statcard, #days .statcard, #places .statcard";
  const FITS = [1, 0.8, 0.62, 0.45];
  const ART_GAP = 10;

  const keyStep = (key) => (FORWARD.includes(key) ? 1 : BACK.includes(key) ? -1 : 0);
  const targetIndex = (current, step, count) => Math.min(count - 1, Math.max(0, current + step));

  const clearOf = (box, blocks, gap) => blocks.every((b) =>
    box.right + gap <= b.left || box.left - gap >= b.right || box.bottom + gap <= b.top || box.top - gap >= b.bottom);
  const bestFit = (fits, isClear) => {
    for (const fit of fits) if (isClear(fit)) return fit;
    return null;
  };

  const letters = (element) => {
    const range = document.createRange();
    const text = [...element.childNodes].find((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
    if (element.classList.contains("big") && text) range.selectNode(text);
    else range.selectNodeContents(element);
    return range.getBoundingClientRect();
  };

  // Keeps each piece of art off the text at this window size: shrink toward its edge, or hide it.
  // Uses layout positions, which the entrance animation's transforms don't affect.
  const placeArt = (screen) => {
    const art = screen.querySelector(":scope > .art");
    if (!art) return;
    const frame = screen.getBoundingClientRect();
    const local = (r) => ({ left: r.left - frame.left, right: r.right - frame.left, top: r.top - frame.top, bottom: r.bottom - frame.top });
    const blocks = [
      ...[...screen.querySelectorAll(TEXT)].filter((e) => e.getClientRects().length).map((e) => local(letters(e))),
      ...[...screen.querySelectorAll(BLOCKS)].filter((e) => e.getClientRects().length).map((e) => local(e.getBoundingClientRect())),
    ].filter((b) => b.right > b.left);
    const flipped = art.classList.contains("art-flip");
    for (const sprite of art.querySelectorAll(".sprite")) {
      sprite.classList.remove("art-off");
      sprite.style.removeProperty("--fit");
      if (!sprite.offsetWidth) continue;
      const fit = bestFit(FITS, (size) => {
        sprite.style.setProperty("--fit", size);
        const left = flipped ? art.clientWidth - sprite.offsetLeft - sprite.offsetWidth : sprite.offsetLeft;
        return clearOf({ left, right: left + sprite.offsetWidth, top: sprite.offsetTop, bottom: sprite.offsetTop + sprite.offsetHeight }, blocks, ART_GAP);
      });
      if (fit === null) sprite.classList.add("art-off");
      else sprite.style.setProperty("--fit", fit);
    }
  };

  // Colored copies of each big number, which collapse into it when its screen appears.
  const addClones = (number) => {
    const text = number.textContent;
    number.classList.add("cloned");
    CLONE_COLORS.forEach((color, i) => {
      const clone = document.createElement("span");
      clone.className = "clone";
      clone.setAttribute("aria-hidden", "true");
      clone.style.setProperty("--c", color);
      clone.style.setProperty("--i", [-2, 2, -1, 1][i]);
      clone.textContent = text;
      number.append(clone);
    });
  };

  const start = () => {
    const screens = [...document.querySelectorAll("section")];
    let current = 0;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!still) document.querySelectorAll(".big").forEach(addClones);

    const seen = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          current = screens.indexOf(entry.target);
          update();
        }
      }
    }, { threshold: 0.55 });

    const prev = document.querySelector(".story-prev");
    const next = document.querySelector(".story-next");
    const update = () => {
      if (prev) prev.disabled = current === 0;
      if (next) next.disabled = current === screens.length - 1;
    };
    const go = (step) => {
      current = targetIndex(current, step, screens.length);
      screens[current].scrollIntoView();
      update();
    };

    screens.forEach((screen) => seen.observe(screen));
    const placeAll = () => screens.forEach(placeArt);
    placeAll();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(placeAll);
    window.addEventListener("load", placeAll);
    let resizing;
    window.addEventListener("resize", () => {
      clearTimeout(resizing);
      resizing = setTimeout(placeAll, 120);
    });
    if (prev) prev.addEventListener("click", () => go(-1));
    if (next) next.addEventListener("click", () => go(1));
    update();

    document.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      const step = keyStep(event.key);
      if (!step) return;
      const target = event.target;
      if (target.closest("input, select, textarea")) return;
      if (event.key === " " && target.closest("a, button")) return;
      if (target.closest(SCROLLS_ITSELF)) return;
      event.preventDefault();
      go(step);
    });

    document.addEventListener("click", (event) => {
      if (event.target.closest(INTERACTIVE) || String(window.getSelection())) return;
      if (window.matchMedia("(pointer: fine)").matches) go(1);
    });
  };

  return { keyStep, targetIndex, clearOf, bestFit, start };
})();

if (typeof module !== "undefined") {
  module.exports = Story;
} else {
  Story.start();
}

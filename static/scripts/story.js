// Moves through the results page one full screen at a time: keys, clicks, the arrows or scrolling.
const Story = (() => {
  const FORWARD = ["ArrowRight", "ArrowDown", "PageDown", " "];
  const BACK = ["ArrowLeft", "ArrowUp", "PageUp"];
  // Clicking these does their own thing instead of moving to the next screen.
  const INTERACTIVE = "a, button, input, select, textarea, label, .wheelstage, .wheelinfo, .rawdata, .xmonth, .xday-list, .xvisit-list, .xchips, .heatmap, .story-nav, .poster, .cardswitch, dialog";
  // Up and down scroll these lists when the keyboard is inside them.
  const SCROLLS_ITSELF = ".wheelinfo, .rawdata, .xday-list, .xvisit-list, .xchips";
  const CLONE_COLORS = ["#afb1ff", "#16d0a6", "#ffe24a", "#fff6e9"];
  // What the art has to stay clear of. Text is measured by its letters, the rest by its box.
  const TEXT = "h1, h2, .big, .caption, .headline, .remark, .notice, .feedback, .stamp, .itemname, .itemvalue";
  const BLOCKS = ".socials, .pitch, .poster, .wheelstage, .wheelinfo, #bluewallchart .statcard, #clock .statcard, #calendar .statcard, #plans .statcard, #tables .statcard, #days .statcard, #places .statcard";
  const FITS = [1, 0.8, 0.62, 0.45];
  const ART_GAP = 10;

  const keyStep = (key, shift = false) => {
    if (key === " ") return shift ? -1 : 1;
    if (shift) return 0;  // shift+arrows extend a text selection
    return FORWARD.includes(key) ? 1 : BACK.includes(key) ? -1 : 0;
  };
  const canScroll = (box) => box.scrollHeight > box.clientHeight || box.scrollWidth > box.clientWidth;
  const targetIndex = (current, step, count) => Math.min(count - 1, Math.max(0, current + step));

  // Holds each screen's color, then eases to the next one as you scroll between them.
  const backdropColor = (colors, tops, scrollY) => {
    if (scrollY <= tops[0]) return colors[0];
    const last = tops.length - 1;
    if (scrollY >= tops[last]) return colors[last];
    let i = 0;
    while (scrollY >= tops[i + 1]) i += 1;
    const t = (scrollY - tops[i]) / (tops[i + 1] - tops[i]);
    if (t === 0) return colors[i];
    const eased = t * t * (3 - 2 * t);
    return `color-mix(in oklab, ${colors[i + 1]} ${(eased * 100).toFixed(1)}%, ${colors[i]})`;
  };

  // How far a screen has moved from the window: 0 when it fills it, -1 or 1 when it's out of view.
  const screenOffset = (scrollY, top, height) => Math.min(1, Math.max(-1, (scrollY - top) / height));

  // One fixed color behind every screen, with each screen's art crossfading in place.
  const startBlending = (screens) => {
    const colors = screens.map((screen) => getComputedStyle(screen).getPropertyValue("--scene").trim());
    const backdrop = document.createElement("div");
    backdrop.className = "story-backdrop";
    backdrop.setAttribute("aria-hidden", "true");
    document.body.prepend(backdrop);
    document.documentElement.classList.add("blend");

    let tops = [];
    let queued = false;
    const last = new Map();
    const draw = () => {
      queued = false;
      const y = window.scrollY;
      backdrop.style.background = backdropColor(colors, tops, y);
      screens.forEach((screen, i) => {
        const offset = screenOffset(y, tops[i], screen.offsetHeight || window.innerHeight);
        if (last.get(screen) === offset) return;
        last.set(screen, offset);
        screen.style.setProperty("--away", Math.abs(offset).toFixed(4));
        const art = screen.querySelector(":scope > .art");
        if (art) art.style.visibility = Math.abs(offset) < 0.5 ? "visible" : "hidden";
      });
    };
    const queue = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(draw);
    };
    const measure = () => {
      tops = screens.map((screen) => screen.offsetTop);
      queue();
    };
    window.addEventListener("scroll", queue, { passive: true });
    window.addEventListener("resize", measure);
    window.addEventListener("load", measure);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
    if (document.fonts) document.fonts.addEventListener("loadingdone", measure);
    tops = screens.map((screen) => screen.offsetTop);
    draw();
  };

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
  // Measures where things will settle, without the entrance animation's movement.
  const placeArt = (screen) => {
    const art = screen.querySelector(":scope > .art");
    if (!art) return;
    const frame = screen.getBoundingClientRect();
    const content = screen.querySelector(":scope > .container, :scope > .shareline");
    const drift = content ? new DOMMatrixReadOnly(getComputedStyle(content).transform).m42 : 0;
    const local = (r) => ({ left: r.left - frame.left, right: r.right - frame.left, top: r.top - frame.top - drift, bottom: r.bottom - frame.top - drift });
    const blocks = [
      ...[...screen.querySelectorAll(TEXT)].filter((e) => e.getClientRects().length).map((e) => local(letters(e))),
      ...[...screen.querySelectorAll(BLOCKS)].filter((e) => e.getClientRects().length).map((e) => local(e.getBoundingClientRect())),
    ].filter((b) => b.right > b.left);
    // The wheel spins in the middle and then slides over, so keep clear of where it ends up too.
    const wheel = screen.querySelector(".wheelstage");
    if (wheel && wheel.offsetParent) {
      const left = wheel.offsetParent.offsetLeft + wheel.offsetLeft;
      const top = wheel.offsetParent.offsetTop + wheel.offsetTop;
      blocks.push({ left, top, right: left + wheel.offsetWidth, bottom: top + wheel.offsetHeight });
    }
    for (const sprite of art.querySelectorAll(".sprite")) {
      sprite.classList.remove("art-off");
      sprite.style.removeProperty("--fit");
      if (!sprite.offsetWidth) continue;
      const fit = bestFit(FITS, (size) => {
        sprite.style.setProperty("--fit", size);
        const left = sprite.offsetLeft;
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
    if (!still) {
      document.querySelectorAll(".big").forEach(addClones);
      startBlending(screens);
    }

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

    // Screens only wait for their animation once this script is running, so a failed load
    // can't leave the page blank.
    document.documentElement.classList.add("js");
    screens.forEach((screen) => seen.observe(screen));
    const placeAll = () => screens.forEach(placeArt);
    placeAll();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(placeAll);
    // The font loads without blocking the page, so it can arrive after everything above.
    if (document.fonts) document.fonts.addEventListener("loadingdone", placeAll);
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
      const step = keyStep(event.key, event.shiftKey);
      if (!step) return;
      const target = event.target;
      if (document.querySelector("dialog[open]")) {
        // The page stays put behind the preview. Space still presses its buttons.
        if (step && event.key !== " ") event.preventDefault();
        return;
      }
      if (target.closest("input, select, textarea")) return;
      if (event.key === " " && target.closest("a, button")) return;
      const scroller = target.closest(SCROLLS_ITSELF);
      if (scroller && canScroll(scroller)) return;
      event.preventDefault();
      go(step);
    });

    document.addEventListener("click", (event) => {
      if (event.target.closest(INTERACTIVE) || String(window.getSelection())) return;
      if (window.matchMedia("(pointer: fine)").matches) go(1);
    });
  };

  return { keyStep, canScroll, targetIndex, backdropColor, screenOffset, clearOf, bestFit, start };
})();

if (typeof module !== "undefined") {
  module.exports = Story;
} else {
  Story.start();
}

// The share screen: flips between the trading card and the receipt, draws the one showing to an
// image in the browser (nothing is sent to the server), and offers to copy, save or share it.
const ShareCard = (() => {
  const W = 1080;
  const H = 1920;
  const INK = "#1c0d0a";
  const CREAM = "#fff6e9";
  const PAPER = "#fffdf6";
  const DISPLAY = "Archivo, Impact, sans-serif";
  const MONO = '"Space Mono", Consolas, monospace';

  const fileName = (semester, style = "") => {
    const base = `umass-dining-wrapped-${semester.toLowerCase().replace(/\s+/g, "-")}`;
    return `${base}${style && style !== "trading" ? `-${style}` : ""}.png`;
  };
  const nextStyle = (style) => (style === "trading" ? "receipt" : "trading");

  // The largest size up to `max` at which `text` fits in `width`.
  const fitSize = (measure, text, max, width) => {
    let size = max;
    while (size > 12 && measure(text, size) > width) size -= 2;
    return size;
  };

  // The space between sections so they fill the room left on the card.
  const sectionGap = (room, used, count, min, max) => {
    if (count < 2) return min;
    return Math.min(max, Math.max(min, (room - used) / (count - 1)));
  };

  // Laptops get Copy and Save. The phone share sheet only makes sense on a touch screen.
  const usesShareSheet = (canShareFiles, touchScreen) => canShareFiles && touchScreen;

  // A name on one line if it stays big enough, otherwise split at the space nearest its middle.
  const nameLines = (value, measure, max, room, min) => {
    const words = value.split(" ");
    if (words.length < 2 || fitSize(measure, value, max, room) >= min) return [value];
    let best = 1;
    let bestDiff = Infinity;
    for (let i = 1; i < words.length; i++) {
      const diff = Math.abs(words.slice(0, i).join(" ").length - words.slice(i).join(" ").length);
      if (diff < bestDiff) { best = i; bestDiff = diff; }
    }
    return [words.slice(0, best).join(" "), words.slice(best).join(" ")];
  };

  const findPersonality = (people, name) => (people || []).find((person) => person.name === name) || null;

  const loadImage = (src) => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });

  const painter = (ctx) => {
    const setFont = (size, weight, family) => {
      ctx.font = `${weight} ${size}px ${family}`;
      if ("fontStretch" in ctx) {
        ctx.fontStretch = "normal";
        if (family === DISPLAY) ctx.fontStretch = "condensed";
      }
    };
    const widthAt = (weight, family) => (text, size) => {
      setFont(size, weight, family);
      return ctx.measureText(text).width;
    };
    const text = (value, x, y, size, { weight = 800, family = DISPLAY, color = INK, align = "left", fit = 0 } = {}) => {
      const final = fit ? fitSize(widthAt(weight, family), value, size, fit) : size;
      setFont(final, weight, family);
      ctx.fillStyle = color;
      ctx.textAlign = align;
      ctx.fillText(value, x, y);
      return final;
    };
    const box = (x, y, w, h, radius, fill) => {
      ctx.fillStyle = fill;
      ctx.beginPath();
      ctx.roundRect(x, y, w, h, radius);
      ctx.fill();
    };
    const picture = (image, x, y, w, h) => {
      const scale = Math.min(w / image.naturalWidth, h / image.naturalHeight);
      const dw = image.naturalWidth * scale;
      const dh = image.naturalHeight * scale;
      ctx.drawImage(image, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
    };
    return { text, box, picture, widthAt };
  };

  const drawTrading = (ctx, data, image) => {
    const p = painter(ctx);
    const left = 78;
    const right = W - 78;
    const inner = right - left;
    ctx.fillStyle = data.tone;
    ctx.fillRect(0, 0, W, H);
    p.box(35, 35, W - 70, H - 70, 34, CREAM);
    p.text(data.owner.toUpperCase(), left, 122, 40);
    p.text(data.semester.toUpperCase(), right, 122, 40, { align: "right" });

    p.box(left - 8, 164, 372, 510, 26, INK);
    p.box(left, 172, 356, 494, 20, "#ffffff");
    p.picture(image, left + 6, 178, 344, 482);
    const nameX = left + 396;
    const nameRoom = right - nameX;
    p.text("PERSONALITY", nameX, 330, 32);
    const lines = nameLines(data.personality.toUpperCase(), p.widthAt(900, DISPLAY), 112, nameRoom, 88);
    const size = Math.min(...lines.map((line) => fitSize(p.widthAt(900, DISPLAY), line, 112, nameRoom)));
    lines.forEach((line, i) => p.text(line, nameX, 330 + (size + 2) * (i + 1), size, { weight: 900 }));
    if (data.plan) {
      const chipY = 352 + (size + 2) * lines.length;
      const chipW = p.widthAt(800, DISPLAY)(data.plan, 34) + 44;
      p.box(nameX, chipY, chipW, 56, 28, data.tone);
      p.text(data.plan, nameX + 22, chipY + 40, 34);
    }

    p.box(left, 712, inner, 158, 22, INK);
    data.stats.forEach((stat, i) => {
      const x = left + (inner / data.stats.length) * (i + 0.5);
      p.text(stat[0], x, 796, 82, { weight: 900, color: CREAM, align: "center", fit: inner / data.stats.length - 24 });
      p.text(stat[1], x, 842, 28, { weight: 700, color: CREAM, align: "center" });
    });

    const heights = data.sections.map((s) => 58 + (s.kind === "tiles" ? 132 : s.rows.length * 56));
    const used = heights.reduce((a, b) => a + b, 0);
    const start = 926;
    const bottom = 1790;
    const gap = sectionGap(bottom - start, used, data.sections.length, 24, 70);
    let y = start;
    data.sections.forEach((section, index) => {
      p.text(section.title.toUpperCase(), left, y + 36, 38, { weight: 900 });
      const top = y + 58;
      if (section.kind === "tiles") {
        const count = section.rows.length;
        const tile = (inner - 12 * (count - 1)) / count;
        section.rows.forEach((row, i) => {
          const x = left + i * (tile + 12);
          ctx.globalAlpha = 0.3;
          p.box(x, top, tile, 122, 16, data.tone);
          ctx.globalAlpha = 1;
          p.text(row[0], x + tile / 2, top + 66, 62, { weight: 900, align: "center", fit: tile - 16 });
          p.text(row[1], x + tile / 2, top + 104, 26, { weight: 700, align: "center", fit: tile - 12 });
        });
      } else {
        const most = section.kind === "rank" ? section.rows[0][1] || 1 : 1;
        section.rows.forEach((row, i) => {
          const rowY = top + 42 + i * 56;
          p.text(row[0], left, rowY, 40, { weight: 700, fit: section.kind === "rank" ? 300 : inner - 150 });
          if (section.kind === "rank") {
            p.box(left + 316, rowY - 26, Math.max(14, 500 * (row[1] / most)), 28, 14, data.tone);
          }
          p.text(String(row[1]), right, rowY, 40, { weight: 900, align: "right" });
        });
      }
      y += heights[index] + gap;
    });
    p.text(`UMASS DINING WRAPPED · ${data.semester.toUpperCase()}`, W / 2, 1836, 30, { align: "center" });
  };

  const drawReceipt = (ctx, data, image) => {
    const p = painter(ctx);
    const left = 86;
    const right = W - 86;
    const inner = right - left;
    const mono = { family: MONO, weight: 700 };
    ctx.fillStyle = data.tone;
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = PAPER;
    ctx.beginPath();
    ctx.moveTo(30, 30);
    ctx.lineTo(W - 30, 30);
    ctx.lineTo(W - 30, H - 56);
    const teeth = 20;
    const tooth = (W - 60) / teeth;
    for (let i = 0; i < teeth; i++) {
      ctx.lineTo(W - 30 - tooth * (i + 0.5), H - 30);
      ctx.lineTo(W - 30 - tooth * (i + 1), H - 56);
    }
    ctx.closePath();
    ctx.fill();

    const dashed = (y) => {
      ctx.strokeStyle = INK;
      ctx.lineWidth = 4;
      ctx.setLineDash([12, 8]);
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(right, y);
      ctx.stroke();
      ctx.setLineDash([]);
    };
    const dotted = (label, value, y, size) => {
      const labelSize = p.text(label, left, y, size, { ...mono, fit: inner - 190 });
      const labelEnd = left + p.widthAt(700, MONO)(label, labelSize);
      const valueStart = right - p.widthAt(700, MONO)(value, size);
      p.text(value, right, y, size, { ...mono, align: "right" });
      ctx.fillStyle = "rgba(28, 13, 10, .4)";
      for (let x = labelEnd + 18; x < valueStart - 12; x += 16) {
        ctx.beginPath();
        ctx.arc(x, y - 4, 2.6, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    p.text("UMASS DINING", W / 2, 124, 66, { ...mono, align: "center" });
    p.text("WRAPPED", W / 2, 192, 66, { ...mono, align: "center" });
    const meta = [data.semester.toUpperCase(), data.guest ? `GUEST: ${data.guest.toUpperCase()}` : "", data.plan ? data.plan.toUpperCase() : ""].filter(Boolean).join(" · ");
    p.text(meta, W / 2, 244, 34, { ...mono, align: "center", fit: inner });
    dashed(274);
    p.box(left, 286, 190, 256, 16, INK);
    p.box(left + 7, 293, 176, 242, 10, "#ffffff");
    p.picture(image, left + 11, 297, 168, 234);
    p.text("YOU ORDERED:", left + 212, 390, 36, mono);
    const room = right - (left + 212);
    const lines = nameLines(data.personality.toUpperCase(), p.widthAt(700, MONO), 66, room, 54);
    const size = Math.min(...lines.map((line) => fitSize(p.widthAt(700, MONO), line, 66, room)));
    lines.forEach((line, i) => p.text(line, left + 212, 392 + (size + 4) * (i + 1), size, mono));
    dashed(552);

    const lineH = 56;
    const heights = data.sections.map((s) => 56 + s.rows.length * lineH);
    const subs = Math.max(0, data.stats.length - 1);
    const totalsH = 92 + subs * 50;
    const footTop = H - 196;
    const used = heights.reduce((a, b) => a + b, 0) + totalsH;
    const start = 584;
    const gap = sectionGap(footTop - start, used, data.sections.length + 1, 12, 46);
    let y = start;
    data.sections.forEach((section, index) => {
      p.text(section.title.toUpperCase(), W / 2, y + 36, 42, { ...mono, align: "center", fit: inner });
      section.rows.forEach((row, i) => {
        const [label, value] = section.kind === "tiles" ? [row[1], row[0]] : row;
        dotted(String(label), String(value), y + 56 + 40 + i * lineH, 46);
      });
      y += heights[index] + gap;
    });
    dashed(y);
    p.text(data.stats[0][1].toUpperCase(), left, y + 66, 60, mono);
    p.text(data.stats[0][0], right, y + 66, 60, { ...mono, align: "right" });
    data.stats.slice(1).forEach((stat, i) => {
      p.text(stat[1].toUpperCase(), left, y + 122 + i * 50, 40, mono);
      p.text(stat[0], right, y + 122 + i * 50, 40, { ...mono, align: "right" });
    });

    ctx.fillStyle = INK;
    let bar = left;
    let wide = false;
    while (bar < right) {
      const width = wide ? 12 : 6;
      ctx.fillRect(bar, footTop + 34, Math.min(width, right - bar), 46);
      bar += width + 8;
      wide = !wide;
    }
    p.text("THANKS FOR EATING WITH US", W / 2, footTop + 124, 32, { ...mono, align: "center" });
  };

  const draw = async (style, data) => {
    await Promise.all([
      document.fonts.load(`900 80px ${DISPLAY}`),
      document.fonts.load(`700 46px ${MONO}`),
    ]).catch(() => {});
    await document.fonts.ready;
    const image = await loadImage(data.image);
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    ctx.textBaseline = "alphabetic";
    (style === "receipt" ? drawReceipt : drawTrading)(ctx, data, image);
    return new Promise((resolve, reject) => canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("no image"))), "image/png"));
  };

  const start = (root, data) => {
    const poster = root.querySelector(".poster");
    const switches = [...root.querySelectorAll(".cardswitch button")];
    const shareButton = root.querySelector(".sharebtn");
    const status = root.querySelector(".sharestatus");
    const dialog = document.querySelector(".sharedialog");
    const preview = dialog.querySelector("img");
    const copyButton = dialog.querySelector(".sharecopy");
    const saveButton = dialog.querySelector(".sharesave");
    const sheetButton = dialog.querySelector(".sharesheet");
    const closeButton = dialog.querySelector(".shareclose");
    const message = dialog.querySelector(".sharemessage");
    const made = new Map();  // style -> {blob, url}
    let style = "trading";

    const show = (next) => {
      style = next;
      poster.dataset.style = style;
      poster.querySelector(".face.trading").setAttribute("aria-hidden", String(style !== "trading"));
      poster.querySelector(".face.receipt").setAttribute("aria-hidden", String(style !== "receipt"));
      switches.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.choice === style)));
    };
    switches.forEach((button) => button.addEventListener("click", () => show(button.dataset.choice)));
    poster.addEventListener("click", () => show(nextStyle(style)));

    // Changes the drawing and name on both cards. The stats stay the same.
    const pickers = [...root.querySelectorAll(".personapick button")];
    const choose = (name) => {
      const person = findPersonality(data.personalities, name);
      if (!person || person.name === data.personality) return;
      data.personality = person.name;
      data.image = person.image;
      poster.querySelectorAll(".hero img").forEach((img) => { img.src = person.image; });
      poster.querySelector(".face.trading .hero img").alt = person.name;
      poster.querySelectorAll(".who").forEach((who) => { who.textContent = person.name; });
      pickers.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.name === name)));
      made.forEach(({ url }) => URL.revokeObjectURL(url));
      made.clear();
    };
    pickers.forEach((button) => button.addEventListener("click", () => choose(button.dataset.name)));
    document.addEventListener("personality-shown", (event) => choose(event.detail.name));

    const image = async () => {
      if (!made.has(style)) {
        const blob = await draw(style, { ...data, image: data.image });
        made.set(style, { blob, url: URL.createObjectURL(blob) });
      }
      return made.get(style);
    };
    const canCopy = Boolean(navigator.clipboard && navigator.clipboard.write && window.ClipboardItem);
    copyButton.hidden = !canCopy;

    // While the preview is open the page behind it stays put, unless the preview itself scrolls.
    const holdPage = (event) => {
      const inPreview = event.target !== dialog && dialog.contains(event.target);
      if (!inPreview || dialog.scrollHeight <= dialog.clientHeight + 1) event.preventDefault();
    };

    shareButton.addEventListener("click", async () => {
      shareButton.disabled = true;
      status.textContent = "Making your card…";
      try {
        const { blob, url } = await image();
        const file = new File([blob], fileName(data.semester, style), { type: "image/png" });
        const canShareFiles = Boolean(navigator.canShare && navigator.canShare({ files: [file] }));
        sheetButton.hidden = !usesShareSheet(canShareFiles, window.matchMedia("(pointer: coarse)").matches);
        preview.src = url;
        preview.alt = style === "receipt" ? "Your receipt share card" : "Your trading card";
        message.textContent = "";
        status.textContent = "";
        dialog.showModal();
        document.addEventListener("wheel", holdPage, { passive: false });
        document.addEventListener("touchmove", holdPage, { passive: false });
      } catch (error) {
        status.textContent = "Couldn't make the card. Try again, or take a screenshot.";
      }
      shareButton.disabled = false;
    });

    copyButton.addEventListener("click", async () => {
      try {
        const { blob } = await image();
        await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
        message.textContent = "Copied. Paste it anywhere.";
      } catch (error) {
        message.textContent = "Your browser blocked copying. Use Save image instead.";
      }
    });
    saveButton.addEventListener("click", async () => {
      const { url } = await image();
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName(data.semester, style);
      document.body.append(link);
      link.click();
      link.remove();
      message.textContent = `Saved as ${link.download}.`;
    });
    sheetButton.addEventListener("click", async () => {
      const { blob } = await image();
      const file = new File([blob], fileName(data.semester, style), { type: "image/png" });
      try {
        await navigator.share({ files: [file], title: "My UMass Dining Wrapped" });
      } catch (error) {
        if (error.name !== "AbortError") message.textContent = "Couldn't open sharing. Use Save image instead.";
      }
    });
    closeButton.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener("close", () => {
      document.removeEventListener("wheel", holdPage);
      document.removeEventListener("touchmove", holdPage);
    });
    show("trading");
  };

  return { fileName, nextStyle, findPersonality, fitSize, nameLines, sectionGap, usesShareSheet, start };
})();

if (typeof module !== "undefined") {
  module.exports = ShareCard;
} else {
  const root = document.querySelector("#card .shareline");
  const data = document.getElementById("share-data");
  if (root && data) ShareCard.start(root, JSON.parse(data.textContent));
}

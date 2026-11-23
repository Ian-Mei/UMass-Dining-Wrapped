// Draws the share card to an image in the browser. Nothing is sent to the server.
const ShareCard = (() => {
  const W = 1080;
  const H = 1920;
  const INK = "#06241e";
  const CREAM = "#fff6e9";

  const fileName = (semester) => `umass-dining-wrapped-${semester.toLowerCase().replace(/\s+/g, "-")}.png`;

  // The largest size up to `max` at which `text` fits in `width`.
  const fitSize = (measure, text, max, width) => {
    let size = max;
    while (size > 12 && measure(text, size) > width) size -= 2;
    return size;
  };

  // Laptops just save the image. A desktop share dialog is a detour on the way to posting it.
  const usesShareSheet = (canShareFiles, touchScreen) => canShareFiles && touchScreen;

  const save = (blob, name) => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 10000);
  };

  const loadImage = (src) => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });

  const draw = async (data) => {
    await document.fonts.ready;
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    const font = (size, weight = 900) => `${weight} ${size}px Archivo, Impact, sans-serif`;
    const fitted = (text, max, width, y, weight = 900) => {
      const size = fitSize((t, s) => { ctx.font = font(s, weight); return ctx.measureText(t).width; }, text, max, width);
      ctx.font = font(size, weight);
      ctx.fillText(text, W / 2, y);
    };

    ctx.fillStyle = CREAM;
    ctx.fillRect(0, 0, W, H);
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";
    if ("fontStretch" in ctx) ctx.fontStretch = "condensed";
    ctx.fillStyle = INK;
    fitted(data.owner.toUpperCase(), 54, 920, 130, 800);

    const picture = await loadImage(data.image);
    const pictureH = 930;
    const pictureW = pictureH * (picture.naturalWidth / picture.naturalHeight);
    ctx.drawImage(picture, (W - pictureW) / 2, 190, pictureW, pictureH);

    fitted(data.personality.toUpperCase(), 136, 940, 1270);

    ctx.fillStyle = INK;
    ctx.beginPath();
    ctx.roundRect(70, 1340, 940, 300, 28);
    ctx.fill();
    ctx.fillStyle = CREAM;
    const stats = JSON.parse(data.stats);
    stats.forEach((stat, i) => {
      const x = 70 + (940 / stats.length) * (i + 0.5);
      ctx.font = font(fitSize((t, s) => { ctx.font = font(s); return ctx.measureText(t).width; }, stat[0], 96, 940 / stats.length - 30));
      ctx.fillText(stat[0], x, 1490);
      ctx.font = font(32, 700);
      ctx.fillText(stat[1], x, 1560);
    });

    ctx.fillStyle = INK;
    fitted(`UMASS DINING WRAPPED · ${data.semester.toUpperCase()}`, 38, 920, 1780, 800);
    return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  };

  const start = (poster, button, status) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      status.textContent = "Making your card…";
      try {
        const blob = await draw(poster.dataset);
        const name = fileName(poster.dataset.semester);
        const file = new File([blob], name, { type: "image/png" });
        const canShareFiles = Boolean(navigator.canShare && navigator.canShare({ files: [file] }));
        if (usesShareSheet(canShareFiles, window.matchMedia("(pointer: coarse)").matches)) {
          try {
            await navigator.share({ files: [file], title: "My UMass Dining Wrapped" });
            status.textContent = "";
          } catch (error) {
            if (error.name === "AbortError") {
              status.textContent = "";
            } else {
              // Phones can refuse if drawing the card took too long after the tap.
              save(blob, name);
              status.textContent = "Saved. Post it wherever you want.";
            }
          }
        } else {
          save(blob, name);
          status.textContent = "Saved. Post it wherever you want.";
        }
      } catch (error) {
        status.textContent = "Couldn't make the card. Try again, or take a screenshot.";
      }
      button.disabled = false;
    });
  };

  return { fileName, fitSize, usesShareSheet, start };
})();

if (typeof module !== "undefined") {
  module.exports = ShareCard;
} else {
  const poster = document.querySelector(".poster");
  if (poster) ShareCard.start(poster, document.querySelector(".sharebtn"), document.querySelector(".sharestatus"));
}

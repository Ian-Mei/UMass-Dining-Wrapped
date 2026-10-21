// "Explore your days" and "Explore your places": the last two screens of the results page.
// Reads the purchases templates/wrapped.html puts in #explorer-data (built by
// wrapped/highlights.py explorer()). Everything happens in the page; nothing is sent anywhere.
// The helpers at the top are tested with `node --test tests/` (tests/explorer.test.js).
const Explorer = (() => {
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December"];
  const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  // "2026-09-14" -> a local Date (not UTC midnight, which can land on the day before).
  const parseDay = (day) => {
    const [y, m, d] = day.split("-").map(Number);
    return new Date(y, m - 1, d);
  };
  const isoDay = (date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const dayLabel = (day) => {
    const d = parseDay(day);
    return `${WEEKDAYS[d.getDay()]}, ${MONTHS[d.getMonth()].slice(0, 3)} ${d.getDate()}`;
  };

  // A month as weeks of cells, Sunday first; null cells pad the first and last week.
  const monthCells = (year, month) => {
    const first = new Date(year, month, 1);
    const days = new Date(year, month + 1, 0).getDate();
    const cells = Array(first.getDay()).fill(null);
    for (let d = 1; d <= days; d++) cells.push(isoDay(new Date(year, month, d)));
    while (cells.length % 7) cells.push(null);
    return cells;
  };

  // Like the streak calendar: one shade per visit, up to 4. Top-ups go with their swipe.
  const visitsByDay = (purchases) => {
    const counts = {};
    for (const p of purchases) if (!p.top_up) counts[p.day] = (counts[p.day] || 0) + 1;
    return counts;
  };
  const level = (visits) => Math.min(visits || 0, 4);

  const money = (n) => `$${n.toFixed(2)}`;
  const tag = (p) => (p.swipes ? `${p.swipes} swipe${p.swipes === 1 ? "" : "s"}` : money(p.dollars));

  // "4 swipes · $3.00", leaving out whichever is zero.
  const totals = (purchases) => {
    const swipes = purchases.reduce((n, p) => n + p.swipes, 0);
    const dollars = purchases.reduce((n, p) => n + p.dollars, 0);
    const parts = [];
    if (swipes) parts.push(`${swipes} swipe${swipes === 1 ? "" : "s"}`);
    if (dollars) parts.push(money(dollars));
    return parts.join(" · ");
  };

  const groupByDay = (purchases) => {
    const groups = new Map();
    for (const p of purchases) {
      if (!groups.has(p.day)) groups.set(p.day, []);
      groups.get(p.day).push(p);
    }
    return groups;
  };

  // ---- Drawing the two screens ----

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const purchaseRow = (p, showPlace) => {
    const row = el("div", "xrow");
    row.append(el("span", "xtime", p.time));
    row.append(el("span", "xplace", showPlace ? p.place : ""));
    const tags = el("span", "xtags");
    if (p.top_up) tags.append(el("span", "xtag topup", "top-up"));
    tags.append(el("span", p.swipes ? "xtag swipe" : "xtag dollars", tag(p)));
    row.append(tags);
    return row;
  };

  const start = (data) => {
    const purchases = data.purchases;
    if (!purchases.length) return;
    const visits = visitsByDay(purchases);
    const byDay = groupByDay(purchases);
    const days = [...byDay.keys()];

    // Explore your days
    const daysCard = document.getElementById("explore-days");
    const monthTitle = daysCard.querySelector(".xmonth-title");
    const grid = daysCard.querySelector(".xmonth");
    const dayHead = daysCard.querySelector(".xday-head");
    const dayList = daysCard.querySelector(".xday-list");
    const prevDay = daysCard.querySelector(".xprev");
    const nextDay = daysCard.querySelector(".xnext");
    let shown = parseDay(days[days.length - 1]);
    let selected = days[days.length - 1];

    const drawMonth = () => {
      monthTitle.textContent = `${MONTHS[shown.getMonth()]} ${shown.getFullYear()}`;
      grid.replaceChildren(...WEEKDAYS.map((d) => el("span", "xweekday", d[0])));
      for (const day of monthCells(shown.getFullYear(), shown.getMonth())) {
        if (!day) { grid.append(el("span", "xcell empty")); continue; }
        const cell = el("button", `xcell l${level(visits[day])}${day === selected ? " sel" : ""}`, String(parseDay(day).getDate()));
        cell.type = "button";
        cell.disabled = !byDay.has(day);
        cell.addEventListener("click", () => selectDay(day));
        grid.append(cell);
      }
    };

    const selectDay = (day) => {
      selected = day;
      shown = parseDay(day);
      const list = byDay.get(day) || [];
      dayHead.replaceChildren(el("span", "", dayLabel(day)), el("span", "xsum", totals(list) || "Nothing bought"));
      dayList.replaceChildren(...list.map((p) => purchaseRow(p, true)));
      const i = days.indexOf(day);
      prevDay.disabled = i <= 0;
      nextDay.disabled = i < 0 || i >= days.length - 1;
      prevDay.textContent = i > 0 ? `← ${dayLabel(days[i - 1])}` : "";
      nextDay.textContent = i >= 0 && i < days.length - 1 ? `${dayLabel(days[i + 1])} →` : "";
      drawMonth();
    };

    daysCard.querySelector(".xmonth-prev").addEventListener("click", () => {
      shown = new Date(shown.getFullYear(), shown.getMonth() - 1, 1);
      drawMonth();
    });
    daysCard.querySelector(".xmonth-next").addEventListener("click", () => {
      shown = new Date(shown.getFullYear(), shown.getMonth() + 1, 1);
      drawMonth();
    });
    prevDay.addEventListener("click", () => selectDay(days[days.indexOf(selected) - 1]));
    nextDay.addEventListener("click", () => selectDay(days[days.indexOf(selected) + 1]));
    selectDay(selected);

    // Explore your places
    const placesCard = document.getElementById("explore-places");
    const chips = placesCard.querySelector(".xchips");
    const summary = placesCard.querySelector(".xplace-sum");
    const note = placesCard.querySelector(".xnote");
    const visitList = placesCard.querySelector(".xvisit-list");

    const selectPlace = (name) => {
      const place = data.places.find((p) => p.name === name) || data.places[0];
      for (const chip of chips.children) chip.classList.toggle("on", chip.dataset.place === place.name);
      const theirs = purchases.filter((p) => p.place === place.name);
      const spent = totals(theirs);
      summary.textContent = `${spent} over ${place.visits} visit${place.visits === 1 ? "" : "s"}`;
      note.textContent = place.note || "";
      note.hidden = !place.note;
      const rows = [];
      for (const [day, list] of groupByDay(theirs)) {
        rows.push(el("div", "xdate", dayLabel(day)));
        for (const p of list) rows.push(purchaseRow(p, false));
      }
      visitList.replaceChildren(...rows);
      visitList.scrollTop = 0;
      chips.querySelector(".on")?.scrollIntoView({ block: "nearest", inline: "nearest" });
    };

    for (const place of data.places) {
      const chip = el("button", "xchip", place.name);
      chip.type = "button";
      chip.dataset.place = place.name;
      chip.addEventListener("click", () => selectPlace(place.name));
      chips.append(chip);
    }
    if (data.places.length) selectPlace(data.places[0].name);

    // Links from the other screens: "See this day", "See every visit", streak calendar squares.
    document.addEventListener("click", (event) => {
      const link = event.target.closest("[data-explore-day], [data-explore-place]");
      if (!link) return;
      event.preventDefault();
      if (link.dataset.exploreDay) {
        selectDay(link.dataset.exploreDay);
        document.getElementById("days").scrollIntoView({ behavior: "smooth" });
      } else {
        selectPlace(link.dataset.explorePlace);
        document.getElementById("places").scrollIntoView({ behavior: "smooth" });
      }
    });
  };

  return { monthCells, visitsByDay, level, tag, totals, groupByDay, dayLabel, start };
})();

if (typeof module !== "undefined") {
  module.exports = Explorer;
} else {
  const data = document.getElementById("explorer-data");
  if (data) Explorer.start(JSON.parse(data.textContent));
}

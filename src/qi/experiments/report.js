"use strict";
const data = JSON.parse(document.getElementById("data").textContent);
const $ = (id) => document.getElementById(id);
const el = (tag, text, parent) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (parent) parent.append(node);
  return node;
};
const svg = (tag, attrs, parent) => {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs))
    node.setAttribute(key, value);
  if (parent) parent.append(node);
  return node;
};
const fmt = (value) => (Number.isFinite(value) ? value.toFixed(2) : "—");
function options(id, entries) {
  const select = $(id);
  select.replaceChildren();
  for (const [value, label] of entries) {
    const option = el("option", label, select);
    option.value = value;
  }
}
function table(id, headers, rows) {
  const target = $(id);
  target.replaceChildren();
  const head = el("tr", undefined, el("thead", undefined, target));
  headers.forEach((h) => el("th", h, head));
  const body = el("tbody", undefined, target);
  for (const row of rows) {
    const tr = el("tr", undefined, body);
    row.forEach((cell) => el("td", String(cell), tr));
  }
}
function bars(id, rows, field) {
  const target = $(id);
  target.replaceChildren();
  if (!rows.length) {
    el("p", "No completed samples for this filter.", target);
    return;
  }
  const chart = svg(
    "svg",
    {
      viewBox: `0 0 550 ${rows.length * 32 + 10}`,
      role: "img",
      "aria-label": field,
    },
    target,
  );
  const max = Math.max(1, ...rows.map((row) => row[field]));
  rows.forEach((row, index) => {
    const y = index * 32;
    svg("text", { x: 0, y: y + 18, "font-size": 11 }, chart).textContent =
      `${row.player} · ${row.budget}`;
    svg(
      "rect",
      {
        x: 255,
        y: y + 5,
        width: (230 * row[field]) / max,
        height: 17,
        fill: "#367e65",
        rx: 2,
      },
      chart,
    );
    svg("text", { x: 493, y: y + 18, "font-size": 11 }, chart).textContent =
      fmt(row[field]);
  });
}
const names = {
  K: "帥",
  A: "仕",
  B: "相",
  N: "馬",
  R: "車",
  C: "炮",
  P: "兵",
  k: "將",
  a: "士",
  b: "象",
  n: "馬",
  r: "車",
  c: "砲",
  p: "卒",
};
function board(id, position, move) {
  const target = $(id);
  target.replaceChildren();
  if (!position?.board) return;
  const drawing = svg(
    "svg",
    {
      viewBox: "0 0 420 465",
      role: "img",
      "aria-label": `${position.side || ""} to move`,
    },
    target,
  );
  svg(
    "rect",
    { x: 0, y: 0, width: 420, height: 465, fill: "#eadcbe", rx: 8 },
    drawing,
  );
  for (let rank = 0; rank < 10; rank++)
    svg(
      "line",
      {
        x1: 30,
        y1: 30 + rank * 44,
        x2: 382,
        y2: 30 + rank * 44,
        stroke: "#9d8b67",
      },
      drawing,
    );
  for (let file = 0; file < 9; file++)
    svg(
      "line",
      {
        x1: 30 + file * 44,
        y1: 30,
        x2: 30 + file * 44,
        y2: 426,
        stroke: "#9d8b67",
      },
      drawing,
    );
  svg(
    "rect",
    { x: 31, y: 207, width: 350, height: 42, fill: "#eadcbe" },
    drawing,
  );
  svg(
    "text",
    {
      x: 210,
      y: 234,
      "text-anchor": "middle",
      "font-size": 18,
      fill: "#8e7959",
    },
    drawing,
  ).textContent = "楚 河         漢 界";
  for (const base of [30, 338]) {
    svg(
      "path",
      {
        d: `M162 ${base}L250 ${base + 88}M250 ${base}L162 ${base + 88}`,
        stroke: "#9d8b67",
        fill: "none",
      },
      drawing,
    );
  }
  if (move && move.length === 4) {
    const point = (m) => [
      30 + (m.charCodeAt(0) - 97) * 44,
      30 + (9 - Number(m[1])) * 44,
    ];
    const a = point(move.slice(0, 2)),
      b = point(move.slice(2));
    svg(
      "line",
      {
        x1: a[0],
        y1: a[1],
        x2: b[0],
        y2: b[1],
        stroke: "#3a8c7a",
        "stroke-width": 6,
        opacity: 0.6,
      },
      drawing,
    );
    svg(
      "circle",
      {
        cx: b[0],
        cy: b[1],
        r: 21,
        fill: "none",
        stroke: "#3a8c7a",
        "stroke-width": 3,
      },
      drawing,
    );
  }
  for (let i = 0; i < 90; i++) {
    const piece = position.board[i];
    if (piece === ".") continue;
    const x = 30 + (i % 9) * 44,
      y = 30 + (9 - Math.floor(i / 9)) * 44;
    svg(
      "circle",
      {
        cx: x,
        cy: y,
        r: 17,
        fill: "#fff6dd",
        stroke: piece === piece.toUpperCase() ? "#a34435" : "#344639",
        "stroke-width": 1.4,
      },
      drawing,
    );
    svg(
      "text",
      {
        x,
        y: y + 7,
        "text-anchor": "middle",
        "font-size": 22,
        fill: piece === piece.toUpperCase() ? "#a34435" : "#344639",
      },
      drawing,
    ).textContent = names[piece];
  }
}
$("title").textContent = data.manifest.plan.name;
$("question").textContent = data.manifest.plan.question;
[
  `${data.status.status} · ${data.completed}/${data.planned} units`,
  `${fmt(data.status.elapsed_seconds)} seconds`,
  "Replay & accounting verified",
  `${data.traces.length} inspected decisions`,
].forEach((text) => (el("span", text, $("status")).className = "badge"));
$("provenance").textContent = JSON.stringify(
  {
    preview: data.preview,
    provenance: data.manifest.provenance,
    plan_sha256: data.manifest.plan_sha256,
    corpus_sha256: data.manifest.corpus_sha256,
    validation: data.validation,
    plan: data.manifest.plan,
  },
  null,
  2,
);
options("budget", [
  ["all", "All"],
  ...data.manifest.plan.budgets.map((v) => [String(v), String(v)]),
]);
options("player", [
  ["all", "All"],
  ...data.manifest.plan.players.map((v) => [v, v]),
]);
options("opening", [
  ["all", "All positions"],
  ...data.manifest.plan.corpus.openings.map((p) => [p.id, p.id]),
]);
function compare() {
  const summary =
    $("opening").value === "all"
      ? data.summary
      : data.by_position[$("opening").value];
  const rows = summary.probes.filter(
    (row) =>
      ($("budget").value === "all" ||
        row.budget === Number($("budget").value)) &&
      ($("player").value === "all" || row.player === $("player").value),
  );
  bars("latency", rows, "mean_ms");
  bars("work", rows, "mean_nodes");
  table(
    "comparison",
    [
      "Player",
      "Budget",
      "Samples / planned",
      "Mean ms",
      "Depth¹",
      "Visits",
      "Q visits²",
      "SEE visits",
      "TT cutoffs / hits",
      "Leaf aborts",
      "Immediate wins",
    ],
    rows.map((r) => [
      r.player,
      r.budget,
      `${r.samples} / ${r.expected}`,
      fmt(r.mean_ms),
      r.player.startsWith("mcts") ? "n/a" : fmt(r.mean_depth),
      fmt(r.mean_nodes),
      fmt(r.mean_qnodes),
      fmt(r.mean_see_nodes),
      `${r.tt_cutoffs} / ${r.tt_hits}`,
      r.leaf_aborts,
      `${r.tactical_solved} / ${r.tactical_tested}`,
    ]),
  );
  $("pair-note").textContent =
    `Only complete color pairs enter these totals; ${summary.unpaired_completed_games} completed games currently lack their partner. ¹ Ordinary alpha-beta depth; not an MCTS metric. ² Q visits can overlap MCTS tree/rollout work; these columns are not additive.`;
  const matches = summary.matches.filter(
    (r) =>
      ($("budget").value === "all" || r.budget === Number($("budget").value)) &&
      ($("player").value === "all" || [r.a, r.b].includes($("player").value)),
  );
  table(
    "matches",
    ["Player A", "Player B", "Budget", "Pairs", "A wins / draws / losses"],
    matches.map((r) => [
      r.a,
      r.b,
      r.budget,
      r.pairs,
      `${r.wins} / ${r.draws} / ${r.losses}`,
    ]),
  );
  const old = $("unit").value;
  const units = data.units.filter(
    (u) =>
      ($("opening").value === "all" || u.job.opening === $("opening").value) &&
      ($("budget").value === "all" ||
        u.job.a.nodes === Number($("budget").value)) &&
      ($("player").value === "all" ||
        [u.job.a.kind, u.job.b?.kind].includes($("player").value)),
  );
  options(
    "unit",
    units.map((u) => [
      u.job.id,
      `${u.job.id} · ${u.job.opening} · ${u.job.a.kind}${u.job.b ? " vs " + u.job.b.kind : ""} · ${u.job.a.nodes} · ${u.status}`,
    ]),
  );
  if (units.some((u) => u.job.id === old)) $("unit").value = old;
  selectUnit();
}
let activeUnit;
function selectUnit() {
  activeUnit = data.units.find((u) => u.job.id === $("unit").value);
  $("ply").max = activeUnit ? activeUnit.turns.length : 0;
  $("ply").value = 0;
  inspectPosition();
}
function timeline() {
  const target = $("timeline");
  target.replaceChildren();
  if (!activeUnit) return;
  const metric = $("metric").value;
  const points = activeUnit.turns
    .map((turn, index) => ({
      index,
      value: turn.choice[metric],
      side: turn.side,
    }))
    .filter(
      (p) =>
        Number.isFinite(p.value) &&
        (metric !== "score" || p.side === $("score-side").value),
    );
  if (!points.length) {
    el("p", "No values for this metric and perspective.", target);
    return;
  }
  const min = Math.min(0, ...points.map((p) => p.value)),
    max = Math.max(1, ...points.map((p) => p.value));
  const chart = svg(
    "svg",
    { viewBox: "0 0 620 185", role: "img", "aria-label": metric },
    target,
  );
  const x = (i) => 45 + (i * 540) / Math.max(1, activeUnit.turns.length - 1),
    y = (v) => 145 - ((v - min) * 125) / (max - min);
  svg(
    "line",
    { x1: 45, y1: y(0), x2: 600, y2: y(0), stroke: "#ccd4c8" },
    chart,
  );
  for (const side of ["red", "black"]) {
    const line = points.filter((p) => p.side === side);
    svg(
      "polyline",
      {
        points: line.map((p) => `${x(p.index)},${y(p.value)}`).join(" "),
        fill: "none",
        stroke: side === "red" ? "#a34435" : "#367e65",
        "stroke-width": 1.5,
      },
      chart,
    );
    for (const p of line) {
      const dot = svg(
        "circle",
        {
          cx: x(p.index),
          cy: y(p.value),
          r: 3,
          fill: side === "red" ? "#a34435" : "#367e65",
          tabindex: 0,
          role: "button",
          "aria-label": `Decision ${p.index + 1}: ${fmt(p.value)}`,
        },
        chart,
      );
      dot.addEventListener("click", () => {
        $("ply").value = p.index;
        inspectPosition();
      });
      dot.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          $("ply").value = p.index;
          inspectPosition();
        }
      });
      svg("title", {}, dot).textContent =
        `Decision ${p.index + 1}: ${fmt(p.value)}`;
    }
  }
  svg("text", { x: 0, y: 20, "font-size": 11 }, chart).textContent = fmt(max);
  svg("text", { x: 0, y: 150, "font-size": 11 }, chart).textContent = fmt(min);
  svg("text", { x: 45, y: 176, "font-size": 11 }, chart).textContent =
    "Click a point to inspect its position · red / black player";
  svg(
    "line",
    {
      x1: x(Number($("ply").value)),
      y1: 10,
      x2: x(Number($("ply").value)),
      y2: 150,
      stroke: "#aa985e",
      "stroke-dasharray": "3 4",
    },
    chart,
  );
}
const shellQuote = (s) => "'" + s.replaceAll("'", "'\\''") + "'";
function inspectPosition() {
  if (!activeUnit) {
    $("board").replaceChildren();
    $("decision").textContent = "No saved units match this filter.";
    $("decision-summary").textContent = "No saved units match this filter.";
    $("position-label").textContent = "";
    $("roots").replaceChildren();
    $("trace-command").textContent = "";
    $("timeline").replaceChildren();
    return;
  }
  const index = Number($("ply").value),
    turn = activeUnit.turns[index];
  board("board", activeUnit.frames[index], turn?.choice.move);
  $("position-label").textContent =
    `${activeUnit.job.opening} · position ${index}/${activeUnit.turns.length} · ${activeUnit.frames[index].side} to move · ${activeUnit.status}${activeUnit.outcome ? " · " + JSON.stringify(activeUnit.outcome) : ""}`;
  $("decision-summary").textContent = turn
    ? `${turn.side} chooses ${turn.choice.move} · ${turn.choice.nodes} visits · ${fmt(turn.choice.elapsed_ms)} ms · ${turn.choice.mcts ? turn.choice.mcts.simulations + " simulations" : "completed depth " + turn.choice.completed_depth}`
    : "Final saved position";
  $("decision").textContent = turn
    ? JSON.stringify(turn, null, 2)
    : "Final saved position. An incomplete unit has no inferred outcome.";
  $("score-note").textContent =
    "Scores belong to the player about to move and its evaluator. Material/positional scores and MCTS bounded estimates are different scales; a zero completed depth is not a searched score.";
  $("roots").replaceChildren();
  if (turn?.choice.mcts) {
    const t = el("table", undefined, $("roots"));
    for (const row of [...turn.choice.mcts.root_moves].sort(
      (a, b) => b.visits - a.visits,
    )) {
      const tr = el("tr", undefined, t);
      [
        row.move,
        `${row.visits} visits`,
        row.mean_value === null ? "unvisited" : fmt(row.mean_value),
      ].forEach((v) => el("td", v, tr));
    }
  }
  $("trace-command").textContent = turn
    ? `uv run qi experiment inspect --run ${shellQuote(data.directory)} --unit ${activeUnit.job.id} --turn ${index} --output ${shellQuote(data.directory + "/traces/" + activeUnit.job.id + "-" + index + ".json")}\nuv run qi experiment report --run ${shellQuote(data.directory)} --output ${shellQuote(data.directory + "/report.html")}`
    : "Select a recorded decision to inspect.";
  timeline();
}
options(
  "trace",
  data.traces.map((t, i) => [
    String(i),
    `${t.unit_id} · decision ${t.turn_index + 1} · ${t.config.kind}`,
  ]),
);
let traceEvents = [],
  traceChildren = new Map();
function inspectEvent(item) {
  let position = item;
  while (!position.board && position.parent !== null)
    position = traceEvents[position.parent];
  board("trace-board", position, item.move);
  $("event").textContent = JSON.stringify(item, null, 2);
}
function drawTrace() {
  const target = $("tree");
  target.replaceChildren();
  const trace = data.traces[Number($("trace").value)];
  if (!trace) {
    $("trace-status").textContent =
      "No traces saved. Select a decision above to generate one, then regenerate this report.";
    return;
  }
  traceEvents = trace.recording.events;
  traceChildren = new Map();
  const roots = [];
  for (const item of traceEvents) {
    if (item.parent === null) roots.push(item);
    else {
      if (!traceChildren.has(item.parent)) traceChildren.set(item.parent, []);
      traceChildren.get(item.parent).push(item);
    }
  }
  $("trace-status").textContent =
    `${trace.recording.complete ? "Complete explored-work recording" : "INCOMPLETE RECORDING — " + trace.recording.dropped_events + " events omitted"} · ${traceEvents.length} events · decision and counters match benchmark · trace time ${fmt(trace.choice.elapsed_ms)} ms (excluded from benchmark)`;
  $("trace-status").className = trace.recording.complete ? "" : "trace-warning";
  const filtered = roots.filter(
    (item) =>
      $("trace-view").value !== "mcts-tree" || item.kind === "mcts-tree",
  );
  appendNodes(target, filtered, 0);
  const first = target.querySelector("details");
  if (first) first.open = true;
  if (!filtered.length)
    el("p", "This trace has no retained MCTS tree.", target);
  if (roots.length) inspectEvent(roots[0]);
}
function appendNodes(parent, items, start) {
  const visible = items.filter(
    (item) => $("show-work").checked || item.kind !== "work",
  );
  for (const item of visible.slice(start, start + 100)) {
    const children = traceChildren.get(item.id) || [];
    const box = el("details", undefined, parent);
    const summary = el(
      "summary",
      `#${item.id} ${item.kind}${item.move ? " · " + item.move : ""}${item.depth !== undefined ? " · depth " + item.depth : ""}${item.value !== undefined ? " · value " + fmt(item.value) : ""}${item.visits !== undefined ? " · visits " + item.visits : ""}${item.reason ? " · " + item.reason : ""}${item.status === "interrupted" ? " · INTERRUPTED" : ""} (${children.length} events)`,
      box,
    );
    const inspect = el("button", "Board & details", summary);
    inspect.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      inspectEvent(item);
    });
    box.addEventListener("toggle", () => {
      if (box.open && !box.dataset.loaded) {
        box.dataset.loaded = "true";
        appendNodes(box, children, 0);
      }
    });
  }
  if (visible.length > start + 100) {
    const more = el(
      "button",
      `Show next ${Math.min(100, visible.length - start - 100)} of ${visible.length - start - 100} events`,
      parent,
    );
    more.addEventListener("click", () => {
      more.remove();
      appendNodes(parent, visible, start + 100);
    });
  }
}
$("opening").addEventListener("change", compare);
$("budget").addEventListener("change", compare);
$("player").addEventListener("change", compare);
$("unit").addEventListener("change", selectUnit);
$("ply").addEventListener("input", inspectPosition);
$("metric").addEventListener("change", timeline);
$("score-side").addEventListener("change", timeline);
$("previous").addEventListener("click", () => {
  $("ply").value = Math.max(0, Number($("ply").value) - 1);
  inspectPosition();
});
$("next").addEventListener("click", () => {
  $("ply").value = Math.min(Number($("ply").max), Number($("ply").value) + 1);
  inspectPosition();
});
for (const id of ["trace", "trace-view", "show-work"])
  $(id).addEventListener("change", drawTrace);
compare();
drawTrace();

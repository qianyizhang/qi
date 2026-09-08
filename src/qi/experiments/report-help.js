/* Glossary definitions come only from docs/glossary/ddd.md via report generation. */
(() => {
  const glossary = data.glossary;
  const names = new Map();
  for (const entry of glossary.entries)
    for (const name of [entry.term, ...entry.aliases])
      names.set(name.toLowerCase(), entry);
  const escape = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Short record keys (a, b, id, …) belong in JSON, not ordinary prose.
  const phrases = [...names.keys()].filter(
    (name) => name.length > 2 && !name.includes("_"),
  );
  const words = new RegExp(
    `(?<![\\w-])(${phrases
      .sort((a, b) => b.length - a.length)
      .map(escape)
      .join("|")})(?![\\w-])`,
    "gi",
  );
  const tooltip = el("div", undefined, document.body);
  tooltip.id = "term-tooltip";
  tooltip.setAttribute("role", "tooltip");
  tooltip.hidden = true;
  let active = null;
  let pinned = false;
  let closing;

  function close() {
    clearTimeout(closing);
    active?.removeAttribute("aria-describedby");
    active = null;
    pinned = false;
    tooltip.hidden = true;
  }
  function position() {
    if (!active?.isConnected) return close();
    const rect = active.getBoundingClientRect();
    const width = tooltip.offsetWidth;
    const height = tooltip.offsetHeight;
    tooltip.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - width - 8))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(rect.bottom + 8, innerHeight - height - 8))}px`;
  }
  function show(trigger) {
    clearTimeout(closing);
    if (active !== trigger) {
      close();
      active = trigger;
      const entry = names.get(trigger.dataset.term.toLowerCase());
      tooltip.replaceChildren();
      el("strong", `${entry.term} · ${entry.chinese}`, tooltip);
      el("p", entry.meaning, tooltip);
      el("p", `Do not confuse with: ${entry.avoid}.`, tooltip).className =
        "muted";
      trigger.setAttribute("aria-describedby", tooltip.id);
    }
    tooltip.hidden = false;
    position();
  }
  function leave() {
    if (!pinned) closing = setTimeout(close, 180);
  }
  function term(text, entry) {
    const button = el("span", text);
    button.className = "glossary-term";
    button.tabIndex = 0;
    button.setAttribute("role", "button");
    button.setAttribute("aria-label", `${text}: explain ${entry.term}`);
    button.dataset.term = entry.term;
    button.addEventListener("pointerenter", (event) => {
      if (event.pointerType !== "touch" && !pinned) show(button);
    });
    button.addEventListener("pointerleave", leave);
    button.addEventListener("focus", () => show(button));
    button.addEventListener("blur", () => {
      if (!pinned) close();
    });
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (active === button && pinned) close();
      else {
        show(button);
        pinned = true;
      }
    });
    button.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        event.stopPropagation();
        button.click();
      }
    });
    return button;
  }
  tooltip.addEventListener("pointerenter", () => clearTimeout(closing));
  tooltip.addEventListener("pointerleave", leave);
  document.addEventListener("pointerdown", (event) => {
    if (!event.target.closest(".glossary-term, #term-tooltip")) close();
  });
  document.addEventListener("focusin", (event) => {
    if (!event.target.closest(".glossary-term, #term-tooltip")) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
  window.addEventListener("resize", () => {
    if (active) position();
  });
  document.addEventListener(
    "scroll",
    () => {
      if (active) position();
    },
    true,
  );

  function annotate(node) {
    if (node.nodeType !== Node.TEXT_NODE) {
      for (const child of [...node.childNodes]) annotate(child);
      return;
    }
    const parent = node.parentElement;
    if (
      !parent ||
      parent.closest(
        ".glossary-term, #glossary-reference, #term-tooltip, svg, script, style, select, button, a, h1, #question",
      )
    )
      return;
    const pre = parent.closest("pre");
    if (pre && !["decision", "event", "provenance"].includes(pre.id)) return;
    const source = node.textContent;
    const pattern = pre ? /"([^"\\]+)"(?=\s*:)/g : words;
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const match of source.matchAll(pattern)) {
      const name = match[1];
      // Stored MCTS-node visits differ from the report's charged-work column.
      const entry =
        name.toLowerCase() === "visits" &&
        (pre || parent.closest("#tree, #roots"))
          ? names.get("mcts node visits")
          : names.get(name.toLowerCase());
      if (!entry) continue;
      const start = match.index + (pre ? 1 : 0);
      fragment.append(source.slice(cursor, start), term(name, entry));
      cursor = start + name.length;
    }
    if (cursor) {
      fragment.append(source.slice(cursor));
      node.replaceWith(fragment);
    }
  }
  for (const root of document.querySelectorAll("header, main")) {
    annotate(root);
    new MutationObserver((changes) => {
      for (const change of changes) {
        if (change.type === "characterData") annotate(change.target);
        else
          for (const child of change.addedNodes)
            if (child.isConnected) annotate(child);
      }
      if (active && !active.isConnected) close();
    }).observe(root, { childList: true, subtree: true, characterData: true });
  }

  function reference() {
    const query = $("glossary-search").value.trim().toLowerCase();
    const entries = glossary.entries.filter((entry) =>
      [entry.term, entry.chinese, ...entry.aliases, entry.meaning].some(
        (value) => value.toLowerCase().includes(query),
      ),
    );
    $("glossary-entries").replaceChildren();
    let category;
    for (const entry of entries) {
      if (category !== entry.category) {
        category = entry.category;
        el("h3", category, $("glossary-entries"));
      }
      const item = el("article", undefined, $("glossary-entries"));
      el("h4", `${entry.term} · ${entry.chinese}`, item);
      el("p", entry.meaning, item);
      el("p", `Do not confuse with: ${entry.avoid}.`, item).className = "muted";
      if (entry.aliases.length)
        el("p", `Also shown as: ${entry.aliases.join(", ")}`, item).className =
          "muted";
    }
    $("glossary-count").textContent =
      `${entries.length} of ${glossary.entries.length} terms`;
  }
  $("glossary-search").addEventListener("input", reference);
  $("open-glossary").addEventListener("click", () => {
    $("glossary-reference").open = true;
    $("glossary-search").focus();
  });
  $("glossary-source").textContent =
    `Definitions: ${glossary.source} · SHA-256 ${glossary.glossary_sha256}. Embedded when this report was generated; separate from experiment provenance.`;
  reference();
})();

import { test, expect, type Page } from "@playwright/test";
async function start(page: Page) {
  await page.goto("/play");
  await expect(page.locator(".board-status")).toContainText(
    "Red to move · Ply 0",
  );
}
async function humanMove(page: Page) {
  await page.getByRole("button", { name: /^b2 red cannon/ }).click();
  await page.getByRole("button", { name: /^e2 empty/ }).click();
  await expect(page.locator(".board-status")).toContainText("Ply 1");
}
async function stored(page: Page) {
  return page.evaluate(
    () =>
      JSON.parse(localStorage.getItem("qi.active-session.v1") ?? "null")
        ?.session,
  );
}
function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
async function delayed(page: Page) {
  await page.addInitScript(() => {
    const fetch = window.fetch.bind(window);
    window.fetch = (input, init) =>
      fetch(input, { ...init, signal: undefined });
  });
  const entered = deferred(),
    released = deferred();
  let calls = 0;
  await page.route("**/api/play/choose", async (route) => {
    calls++;
    const response = await route.fetch();
    if (calls === 1) {
      entered.resolve();
      await released.promise;
    }
    await route.fulfill({ response });
  });
  return {
    entered: entered.promise,
    release: released.resolve,
    calls: () => calls,
  };
}
async function choose(page: Page, side: string, player: string) {
  await page.getByLabel(`${side} player`, { exact: true }).selectOption(player);
  await expect
    .poll(async () => (await stored(page))?.controllers[side].player)
    .toBe(player);
}

test("human vs alpha-beta, session export, replay and paused restore", async ({
  page,
}) => {
  await start(page);
  await choose(page, "black", "alphabeta");
  await page.getByRole("button", { name: "Resume", exact: true }).click();
  await humanMove(page);
  await expect(page.locator(".board-status")).toContainText(
    "Red to move · Ply 2",
  );
  await page.getByText("Last computer move", { exact: true }).click();
  await expect(page.getByText(/alphabeta-material-v1/)).toBeVisible();
  const saved = await stored(page);
  expect(saved.history).toHaveLength(2);
  expect(saved.history[1].config.kind).toBe("alphabeta");
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export session", exact: true })
    .click();
  expect((await download).suggestedFilename()).toBe("qi-session.json");
  await page
    .getByRole("button", { name: "Previous position", exact: true })
    .click();
  await expect(page.locator(".board-status")).toContainText("Ply 1");
  await page
    .getByRole("button", { name: "Live position", exact: true })
    .click();
  await page.reload();
  await expect(page.locator(".board-status")).toContainText("Ply 2");
  await expect(
    page.getByRole("button", { name: "Resume", exact: true }),
  ).toBeVisible();
});

test("independent computer sides step, change settings and pause on navigation", async ({
  page,
}) => {
  await start(page);
  await choose(page, "red", "mcts");
  await choose(page, "black", "alphabeta");
  await page.getByLabel("red Visit budget", { exact: true }).fill("32");
  await page.getByRole("button", { name: "Apply red settings" }).click();
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.locator(".board-status")).toContainText("Ply 1");
  await page.getByLabel("black Visit budget", { exact: true }).fill("16");
  await page.getByRole("button", { name: "Apply black settings" }).click();
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.locator(".board-status")).toContainText("Ply 2");
  const data = await stored(page);
  expect(data.history[0].config.nodes).toBe(32);
  expect(data.history[1].config.nodes).toBe(16);
  await page.getByRole("button", { name: "Resume", exact: true }).click();
  await expect
    .poll(async () => (await stored(page)).history.length)
    .toBeGreaterThan(2);
  await page.getByRole("link", { name: "Experiments", exact: true }).click();
  const moves = (await stored(page)).history.length;
  await page.getByRole("link", { name: "Play", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Resume", exact: true }),
  ).toBeVisible();
  expect((await stored(page)).history.length).toBe(moves);
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  expect((await stored(page)).history.length).toBe(moves);
  await page.goBack();
  await expect(page).toHaveURL(/\/experiments$/);
  await page.goForward();
  await expect(page).toHaveURL(/\/play$/);
  await expect(
    page.getByRole("button", { name: "Resume", exact: true }),
  ).toBeVisible();
  expect((await stored(page)).history.length).toBe(moves);
});

for (const action of [
  "new",
  "settings",
  "navigate",
  "replay",
  "import",
] as const) {
  test(`late response cannot overwrite ${action}`, async ({ page }) => {
    const delay = await delayed(page);
    await start(page);
    await humanMove(page);
    await choose(page, "black", "random");
    await page.getByRole("button", { name: "Step", exact: true }).click();
    await delay.entered;
    if (action === "new")
      await page.getByRole("button", { name: "New game", exact: true }).click();
    if (action === "settings") {
      await page.getByRole("button", { name: "Cancel move" }).click();
      await choose(page, "black", "alphabeta");
    }
    if (action === "navigate")
      await page.getByRole("link", { name: "Home", exact: true }).click();
    if (action === "replay")
      await page
        .getByRole("button", { name: "Previous position", exact: true })
        .click();
    if (action === "import") {
      const snapshot = (await page.request.post("/api/new")).json();
      await page.getByRole("button", { name: "Import", exact: true }).click();
      await page
        .getByLabel("Imported JSON")
        .fill(JSON.stringify((await snapshot).snapshot));
      await page.getByRole("button", { name: "Load JSON" }).click();
    }
    if (action === "new" || action === "import")
      await expect
        .poll(async () => (await stored(page)).snapshot.moves.length)
        .toBe(0);
    delay.release();
    await page.getByRole("link", { name: "Play", exact: true }).click();
    await expect(page.locator(".board-status")).toContainText(
      `Ply ${action === "new" || action === "import" || action === "replay" ? 0 : 1}`,
    );
    expect((await stored(page)).snapshot.moves.length).toBe(
      action === "new" || action === "import" ? 0 : 1,
    );
    expect(delay.calls()).toBe(1);
  });
}

test("failure preserves position and retries only on explicit Step", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/play/choose", async (route) => {
    calls++;
    if (calls === 1)
      await route.fulfill({
        status: 409,
        json: { error: { message: "Engine unavailable" } },
      });
    else await route.continue();
  });
  await start(page);
  await choose(page, "red", "random");
  await page.getByRole("button", { name: "Resume", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Engine unavailable");
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  expect(calls).toBe(1);
  await expect(page.locator(".board-status")).toContainText("Ply 0");
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.locator(".board-status")).toContainText("Ply 1");
  expect(calls).toBe(2);
});

test("multiple tabs cannot overwrite a newer session", async ({
  page,
  context,
}) => {
  await start(page);
  await choose(page, "red", "random");
  const other = await context.newPage();
  await other.goto("/play");
  await expect(other.locator(".board-status")).toContainText("Ply 0");
  await page.bringToFront();
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.locator(".board-status")).toContainText("Ply 1");
  await expect(
    other.getByRole("button", { name: "Load saved session", exact: true }),
  ).toBeVisible();
  await other
    .getByRole("button", { name: "Load saved session", exact: true })
    .click();
  await expect(other.locator(".board-status")).toContainText("Ply 1");
  await expect(
    other.getByRole("button", { name: "Resume", exact: true }),
  ).toBeVisible();
});

test("restored missing resources stay paused and snapshot import has unknown history", async ({
  page,
}) => {
  await start(page);
  await humanMove(page);
  const data = await stored(page);
  data.controllers.black = {
    player: "missing-trained",
    settings: {},
    binding_sha256: "a".repeat(64),
    checkpoint_sha256: "b".repeat(64),
  };
  data.changes.push({ ply: 1, controllers: data.controllers });
  await page.evaluate(
    (session) =>
      localStorage.setItem(
        "qi.active-session.v1",
        JSON.stringify({ revision: "restore", session }),
      ),
    data,
  );
  await page.reload();
  await expect(
    page.getByText(/black: saved player is unavailable/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Resume", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Import", exact: true }).click();
  await page.getByLabel("Imported JSON").fill(JSON.stringify(data.snapshot));
  await page.getByRole("button", { name: "Load JSON" }).click();
  await expect(
    page.getByText("Player attribution unknown for imported history."),
  ).toBeVisible();
  expect((await stored(page)).unknown_prefix).toBe(1);
});

test("catalog extension and search diagnostics work without a UI allowlist", async ({
  page,
}) => {
  await page.route("**/api/players", async (route) => {
    const response = await route.fetch();
    const players = await response.json();
    players.push({
      ...players.find((p: { id: string }) => p.id === "alphabeta"),
      id: "future-player",
      label: "Future player",
    });
    await route.fulfill({ json: players });
  });
  await start(page);
  await expect(
    page
      .getByLabel("red player", { exact: true })
      .locator("option[value=future-player]"),
  ).toHaveCount(1);
  await choose(page, "red", "mcts");
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.locator(".board-status")).toContainText("Ply 1");
  await page.getByText("Last computer move", { exact: true }).click();
  await expect(
    page.getByRole("region", { name: "MCTS root move statistics" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("terminal imports do not trigger moves and invalid settings never corrupt restoration", async ({
  page,
}) => {
  await start(page);
  const snapshot = (await (await page.request.post("/api/new")).json())
    .snapshot;
  snapshot.moves = [
    "b0c2",
    "b9c7",
    "c2b0",
    "c7b9",
    "b0c2",
    "b9c7",
    "c2b0",
    "c7b9",
  ];
  await page.getByRole("button", { name: "Import", exact: true }).click();
  await page.getByLabel("Imported JSON").fill(JSON.stringify(snapshot));
  await page.getByRole("button", { name: "Load JSON" }).click();
  await expect(page.locator(".board-status")).toContainText("repetition");
  await expect(
    page.getByRole("button", { name: "Step", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "New game", exact: true }).click();
  await choose(page, "red", "alphabeta");
  await page.getByLabel("red Visit budget", { exact: true }).fill("");
  await page.getByRole("heading", { name: "Play & explore" }).click();
  await page.reload();
  await expect(page.locator(".board-status")).toContainText("Ply 0");
  expect((await stored(page)).controllers.red.settings.nodes).toBe(128);
});

test("catalog failure keeps human play available and can be retried", async ({
  page,
}) => {
  let failed = true;
  await page.route("**/api/players", async (route) => {
    if (failed)
      await route.fulfill({
        status: 503,
        json: { error: { message: "Catalog unavailable" } },
      });
    else await route.continue();
  });
  await start(page);
  await humanMove(page);
  await expect(page.getByRole("alert")).toContainText("Catalog unavailable");
  failed = false;
  await page
    .getByRole("button", { name: "Refresh players", exact: true })
    .click();
  await expect(
    page
      .getByLabel("black player", { exact: true })
      .locator('option[value="alphabeta"]'),
  ).toHaveCount(1);
});

test("settings can be typed without interrupted focus and apply together", async ({
  page,
}) => {
  await start(page);
  await choose(page, "red", "alphabeta");
  const changes = (await stored(page)).changes.length;
  const budget = page.getByLabel("red Visit budget", { exact: true });
  await budget.fill("");
  await budget.pressSequentially("256", { delay: 40 });
  await expect(budget).toBeFocused();
  await expect(budget).toHaveValue("256");
  await page.getByLabel("red Depth limit", { exact: true }).fill("3");
  expect((await stored(page)).controllers.red.settings.nodes).toBe(128);
  await expect(
    page.getByRole("button", { name: "Step", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Apply red settings" }).click();
  await expect
    .poll(async () => (await stored(page)).controllers.red.settings.nodes)
    .toBe(256);
  const saved = await stored(page);
  expect(saved.controllers.red.settings.depth).toBe(3);
  expect(saved.changes).toHaveLength(changes + 1);
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect(page.locator(".board-status")).toContainText("Ply 1");
  expect((await stored(page)).history[0].config.nodes).toBe(256);
});

for (const status of [200, 503]) {
  test(`cancelled settings validation releases the lock and ignores a late ${status} response`, async ({
    page,
  }) => {
    await page.addInitScript(() => {
      const fetch = window.fetch.bind(window);
      window.fetch = (input, init) =>
        fetch(input, { ...init, signal: undefined });
    });
    await start(page);
    await humanMove(page);
    const before = await stored(page);
    const entered = deferred(),
      released = deferred();
    await page.route("**/api/play/controller/inspect", async (route) => {
      const controller = route.request().postDataJSON();
      if (controller.player !== "alphabeta") return route.continue();
      entered.resolve();
      await released.promise;
      await route.fulfill({
        status,
        json:
          status === 200
            ? controller
            : { error: { message: "Obsolete settings failure" } },
      });
    });
    try {
      await page
        .getByLabel("red player", { exact: true })
        .selectOption("alphabeta");
      await entered.promise;
      await page.getByRole("link", { name: "Reference", exact: true }).click();
      await page.getByRole("link", { name: "Play", exact: true }).click();
      // Navigation cancels the edit and must release the cross-tab write lock.
      await choose(page, "black", "random");
      const response = page.waitForResponse("**/api/play/controller/inspect");
      released.resolve();
      await response;
      await page.getByRole("button", { name: "Flip board" }).click();
      const saved = await stored(page);
      expect(saved.controllers.red.player).toBe("human");
      expect(saved.controllers.black.player).toBe("random");
      expect(saved.changes).toHaveLength(before.changes.length + 1);
      await expect(page.getByRole("alert")).toHaveCount(0);
    } finally {
      released.resolve();
    }
  });
}

test("clearing saved storage in another tab pauses the stale session", async ({
  page,
  context,
}) => {
  await start(page);
  await humanMove(page);
  const other = await context.newPage();
  await other.goto("/play");
  await expect(other.locator(".board-status")).toContainText("Ply 1");
  await other.evaluate(() => localStorage.clear());
  await expect(page.getByRole("alert")).toContainText("Another tab changed");
  await page.getByRole("button", { name: "Load saved session" }).click();
  await expect(page.locator(".board-status")).toContainText("Ply 0");
  await expect(page.getByRole("alert")).toHaveCount(0);
});

for (const action of ["new", "import"] as const) {
  test(`late replay cannot replace a ${action} session`, async ({ page }) => {
    await page.addInitScript(() => {
      const fetch = window.fetch.bind(window);
      window.fetch = (input, init) =>
        fetch(input, { ...init, signal: undefined });
    });
    await start(page);
    await humanMove(page);
    await page.getByRole("button", { name: /^b7 black cannon/ }).click();
    await page.getByRole("button", { name: /^e7 empty/ }).click();
    await expect(page.locator(".board-status")).toContainText("Ply 2");
    const entered = deferred(),
      released = deferred();
    await page.route("**/api/inspect", async (route) => {
      const response = await route.fetch();
      if (route.request().postDataJSON().snapshot.moves.length === 1) {
        entered.resolve();
        await released.promise;
      }
      await route.fulfill({ response });
    });
    await page.getByRole("button", { name: "Previous position" }).click();
    await entered.promise;
    if (action === "new")
      await page.getByRole("button", { name: "New game", exact: true }).click();
    else {
      const initial = await (await page.request.post("/api/new")).json();
      await page.getByRole("button", { name: "Import", exact: true }).click();
      await page
        .getByLabel("Imported JSON")
        .fill(JSON.stringify(initial.snapshot));
      await page.getByRole("button", { name: "Load JSON" }).click();
    }
    await expect(page.locator(".board-status")).toContainText("Ply 0");
    released.resolve();
    await page.getByRole("button", { name: "Flip board" }).click();
    await expect(page.locator(".board-status")).toContainText("Ply 0");
    await expect(page.locator(".board-status")).not.toContainText("Replay");
    expect((await stored(page)).snapshot.moves).toHaveLength(0);
  });
}

test("damaged saved data can be backed up before starting a new session", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("qi.active-session.v1", "{damaged"),
  );
  await page.goto("/play");
  await page
    .getByRole("button", { name: "Back up saved data and start new" })
    .click();
  await expect(page.locator(".board-status")).toContainText("Ply 0");
  expect(
    await page.evaluate(() =>
      Object.keys(localStorage)
        .filter((key) => key.startsWith("qi.active-session.v1.backup."))
        .map((key) => localStorage.getItem(key)),
    ),
  ).toEqual(["{damaged"]);
  await humanMove(page);
});

test("cancelling a stalled response body releases the session lock", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const fetch = window.fetch.bind(window);
    const control = window as unknown as {
      bodyWaiting: boolean;
      releaseBody: () => void;
    };
    window.fetch = async (input, init) => {
      const response = await fetch(input, { ...init, signal: undefined });
      if (String(input).endsWith("/play/choose")) {
        const data = await response.json();
        Object.defineProperty(response, "json", {
          value: () =>
            new Promise((resolve) => {
              control.bodyWaiting = true;
              control.releaseBody = () => resolve(data);
            }),
        });
      }
      return response;
    };
  });
  await start(page);
  await choose(page, "red", "random");
  await page.getByRole("button", { name: "Step", exact: true }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () => (window as unknown as { bodyWaiting: boolean }).bodyWaiting,
      ),
    )
    .toBe(true);
  await page.getByRole("button", { name: "New game", exact: true }).click();
  await expect
    .poll(async () => (await stored(page)).controllers.red.player)
    .toBe("human");
  await page.evaluate(() =>
    (window as unknown as { releaseBody: () => void }).releaseBody(),
  );
  await humanMove(page);
  expect((await stored(page)).history[0].controller.player).toBe("human");
});

test("invalid imports preserve the session and keep errors inside the dialog", async ({
  page,
}) => {
  await start(page);
  await humanMove(page);
  const before = await page.evaluate(() =>
    localStorage.getItem("qi.active-session.v1"),
  );
  await page.getByRole("button", { name: "Import", exact: true }).click();
  const dialog = page.getByRole("dialog");
  for (const input of [
    "{bad",
    "null",
    "false",
    "0",
    '""',
    "[]",
    '{"moves":["invalid"]}',
    '{"format":"invalid"}',
  ]) {
    await dialog.getByLabel("Imported JSON").fill(input);
    await dialog.getByRole("button", { name: "Load JSON" }).click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    await expect(dialog.getByLabel("Imported JSON")).toHaveValue(input);
    expect(
      await page.evaluate(() => localStorage.getItem("qi.active-session.v1")),
    ).toBe(before);
    await expect(page.locator(".board-status")).toContainText("Ply 1");
  }
});

test("import closes only after validation and a successful storage write", async ({
  page,
}) => {
  await start(page);
  await humanMove(page);
  const before = await page.evaluate(() =>
    localStorage.getItem("qi.active-session.v1"),
  );
  const initial = await (await page.request.post("/api/new")).json();
  const entered = deferred(),
    released = deferred();
  await page.route("**/api/inspect", async (route) => {
    const response = await route.fetch();
    entered.resolve();
    await released.promise;
    await route.fulfill({ response });
  });
  await page.getByRole("button", { name: "Import", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Imported JSON")
    .fill(JSON.stringify(initial.snapshot));
  await dialog.getByRole("button", { name: "Load JSON" }).click();
  await entered.promise;
  await expect(dialog.getByRole("status")).toContainText(
    "Validating and saving",
  );
  await expect(
    dialog.getByRole("button", { name: "Close", exact: true }),
  ).toBeDisabled();
  expect(
    await page.evaluate(() => localStorage.getItem("qi.active-session.v1")),
  ).toBe(before);
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (key === "qi.active-session.v1")
        throw new Error("Storage quota exceeded");
      return original.call(this, key, value);
    };
    (window as unknown as { restoreStorage: () => void }).restoreStorage =
      () => {
        Storage.prototype.setItem = original;
      };
  });
  released.resolve();
  await expect(dialog.getByRole("alert")).toContainText(
    "Storage quota exceeded",
  );
  await expect(dialog.getByLabel("Imported JSON")).toHaveValue(
    JSON.stringify(initial.snapshot),
  );
  expect(
    await page.evaluate(() => localStorage.getItem("qi.active-session.v1")),
  ).toBe(before);
  await page.evaluate(() =>
    (window as unknown as { restoreStorage: () => void }).restoreStorage(),
  );
  await dialog.getByRole("button", { name: "Load JSON" }).click();
  await expect(dialog).toBeHidden();
  await expect(page.locator(".board-status")).toContainText("Ply 0");
  expect((await stored(page)).snapshot.moves).toHaveLength(0);
});

test("board has one Tab stop and arrow movement follows its orientation", async ({
  page,
}) => {
  await start(page);
  const board = page.getByRole("group", { name: "Chinese chess board" });
  await expect(board.locator('[tabindex="0"]')).toHaveCount(1);
  const square = (name: string) =>
    board.getByRole("button", { name: new RegExp(`^${name} `) });
  await square("a0").focus();
  await page.keyboard.press("ArrowLeft");
  await expect(square("a0")).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowUp");
  await expect(square("b1")).toBeFocused();
  await expect(square("b1")).toHaveCSS("outline-style", "solid");
  await page.getByRole("button", { name: "Flip board" }).click();
  await square("b1").focus();
  await page.keyboard.press("ArrowUp");
  await expect(square("b0")).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowLeft");
  await expect(square("c1")).toBeFocused();
  await page.getByRole("button", { name: "Flip board" }).click();
  await square("b2").focus();
  await page.keyboard.press("Enter");
  for (let i = 0; i < 3; i++) await page.keyboard.press("ArrowRight");
  await expect(square("e2")).toBeFocused();
  await page.keyboard.press("Space");
  await expect(page.locator(".board-status")).toContainText("Ply 1");
  await expect(board.locator('[tabindex="0"]')).toHaveCount(1);
  await page.keyboard.press("Tab");
  expect(
    await board.evaluate((element) => element.contains(document.activeElement)),
  ).toBe(false);
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  await expect(nav.getByRole("link")).toHaveCount(7);
  for (const link of await nav.getByRole("link").all())
    await expect(link).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("non-JSON server failures explain the transport problem", async ({
  page,
}) => {
  await page.route("**/api/players", (route) =>
    route.fulfill({
      status: 502,
      contentType: "text/html",
      body: "<h1>Bad gateway</h1>",
    }),
  );
  await start(page);
  await expect(page.getByRole("alert")).toContainText("502");
  await expect(page.getByRole("alert")).toContainText("without valid JSON");
  await humanMove(page);
});

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

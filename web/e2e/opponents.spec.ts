import { test, expect, type Page } from "@playwright/test";

async function start(page: Page) {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Red to move" }),
  ).toBeVisible();
}

async function humanMove(page: Page) {
  await page.getByRole("button", { name: /^b2 red cannon/ }).click();
  await page.getByRole("button", { name: /^e2 empty/ }).click();
}

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

async function delayFirstOpponent(page: Page) {
  // Deliberately ignore AbortSignal to prove late results cannot overwrite newer state.
  await page.addInitScript(() => {
    const fetch = window.fetch.bind(window);
    window.fetch = (input, init) =>
      fetch(input, { ...init, signal: undefined });
  });
  const entered = deferred(),
    released = deferred();
  let calls = 0;
  await page.route("**/api/opponent", async (route) => {
    calls += 1;
    if (calls > 1) return route.continue();
    const response = await route.fetch();
    entered.resolve();
    await released.promise;
    await route.fulfill({ response });
  });
  return {
    entered: entered.promise,
    release: released.resolve,
    calls: () => calls,
  };
}

async function settleResponse(page: Page, release: () => void) {
  const response = page.waitForResponse("**/api/opponent");
  release();
  await (await response).finished();
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      ),
  );
}

test("human Red plays alpha-beta, exports and replays the resulting game", async ({
  page,
}) => {
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("alphabeta");
  await humanMove(page);
  await expect(page.locator(".moves li")).toHaveCount(2);
  await expect(
    page.getByRole("heading", { name: "Red to move" }),
  ).toBeVisible();
  await page.getByText("Last computer move", { exact: true }).click();
  await expect(page.getByText(/alphabeta-material-v1/)).toBeVisible();
  await page.getByRole("button", { name: "Replay start", exact: true }).click();
  await expect(
    page.getByText("Viewing history.", { exact: false }),
  ).toBeVisible();
  await expect(page.locator(".moves li")).toHaveCount(2);
  await page.getByRole("button", { name: "Latest move", exact: true }).click();
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export game ↓", exact: true })
    .click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const chunk of stream!) chunks.push(chunk);
  const snapshot = JSON.parse(Buffer.concat(chunks).toString());
  expect(snapshot.moves).toHaveLength(2);
  await page.locator('input[type="file"]').setInputFiles({
    name: "saved.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(snapshot)),
  });
  await expect(page.locator(".moves li")).toHaveCount(2);
  await page.screenshot({
    path: test.info().outputPath("opponent-board.png"),
    fullPage: true,
  });
});

test("human Black waits for random Red; switching to pass-and-play permits human moves", async ({
  page,
}) => {
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("random");
  await page.getByLabel("You play", { exact: true }).selectOption("black");
  await expect(page.locator(".moves li")).toHaveCount(1);
  await expect(
    page.getByRole("heading", { name: "Black to move" }),
  ).toBeVisible();
  await page.getByLabel("Opponent", { exact: true }).selectOption("human");
  await page.getByRole("button", { name: /^b9 black horse/ }).click();
  await page.getByRole("button", { name: /^c7 empty/ }).click();
  await expect(page.locator(".moves li")).toHaveCount(2);
});

test("opponent failure preserves the game and only retries on request", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/opponent", async (route) => {
    calls += 1;
    if (calls === 1)
      return route.fulfill({
        status: 503,
        json: { error: { message: "Opponent unavailable" } },
      });
    return route.continue();
  });
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("random");
  await humanMove(page);
  await expect(page.getByRole("alert")).toHaveText("Opponent unavailable");
  await expect(page.locator(".moves li")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Retry opponent" }),
  ).toBeVisible();
  expect(calls).toBe(1);
  await page.getByRole("button", { name: "Retry opponent" }).click();
  await expect(page.locator(".moves li")).toHaveCount(2);
  expect(calls).toBe(2);
});

test("new game rejects an old opponent response even when abort is ignored", async ({
  page,
}) => {
  const delayed = await delayFirstOpponent(page);
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("random");
  await humanMove(page);
  await delayed.entered;
  await expect(
    page.getByRole("heading", { name: "Computer is thinking…" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /^b9 black horse/ }),
  ).toHaveAttribute("aria-disabled", "true");
  await page.getByRole("button", { name: "New game ↗", exact: true }).click();
  await page
    .getByRole("button", { name: "Start new game", exact: true })
    .click();
  await expect(page.locator(".moves li")).toHaveCount(0);
  await settleResponse(page, delayed.release);
  await expect(page.locator(".moves li")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Red to move" }),
  ).toBeVisible();
});

test("replay cancels thinking; latest resumes from the preserved live game", async ({
  page,
}) => {
  const delayed = await delayFirstOpponent(page);
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("random");
  await humanMove(page);
  await delayed.entered;
  await page.getByRole("button", { name: "Replay start", exact: true }).click();
  await expect(
    page.getByText("Viewing history.", { exact: false }),
  ).toBeVisible();
  await settleResponse(page, delayed.release);
  await expect(page.locator(".moves li")).toHaveCount(1);
  await expect(
    page.getByText("Viewing history.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Latest move", exact: true }).click();
  await expect(page.locator(".moves li")).toHaveCount(2);
  expect(delayed.calls()).toBe(2);
});

test("terminal imports never request an opponent move", async ({
  page,
  request,
}) => {
  let calls = 0;
  page.on("request", (req) => {
    if (req.url().endsWith("/api/opponent")) calls += 1;
  });
  await start(page);
  const snapshot = (await (await request.post("/api/new")).json()).snapshot;
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
  await page.locator('input[type="file"]').setInputFiles({
    name: "draw.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(snapshot)),
  });
  await expect(
    page.getByRole("heading", { name: "Draw", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Opponent", { exact: true }).selectOption("alphabeta");
  await expect(
    page.getByRole("heading", { name: "Draw", exact: true }),
  ).toBeVisible();
  expect(calls).toBe(0);
});

test("switching opponents cancels an outstanding computer turn", async ({
  page,
}) => {
  const delayed = await delayFirstOpponent(page);
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("random");
  await humanMove(page);
  await delayed.entered;
  await page.getByLabel("Opponent", { exact: true }).selectOption("human");
  await settleResponse(page, delayed.release);
  await expect(page.locator(".moves li")).toHaveCount(1);
  await expect(
    page.getByRole("heading", { name: "Black to move" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^b9 black horse/ }).click();
  await page.getByRole("button", { name: /^c7 empty/ }).click();
  await expect(page.locator(".moves li")).toHaveCount(2);
});

test("import during search survives an old opponent response", async ({
  page,
  request,
}) => {
  const delayed = await delayFirstOpponent(page);
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("random");
  await humanMove(page);
  await delayed.entered;
  const snapshot = (await (await request.post("/api/new")).json()).snapshot;
  await page.locator('input[type="file"]').setInputFiles({
    name: "fresh.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(snapshot)),
  });
  await expect(page.locator(".moves li")).toHaveCount(0);
  await settleResponse(page, delayed.release);
  await expect(page.locator(".moves li")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Red to move" }),
  ).toBeVisible();
});

test("quiescence is discovered and shows its extra tactical work", async ({
  page,
}) => {
  await start(page);
  await expect(
    page.getByRole("option", {
      name: "Computer · alpha-beta + quiescence",
      exact: true,
    }),
  ).toHaveCount(1);
  await page.getByLabel("Opponent", { exact: true }).selectOption("quiescence");
  await page.getByLabel("You play", { exact: true }).selectOption("black");
  await expect(page.locator(".moves li")).toHaveCount(1);
  await expect(
    page.getByRole("heading", { name: "Black to move" }),
  ).toBeVisible();
  await page.getByText("Last computer move", { exact: true }).click();
  await expect(page.getByText(/alphabeta-quiescence-v1/)).toBeVisible();
  await expect(page.getByText(/quiescence nodes/)).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("quiescence-board.png"),
    fullPage: true,
  });
});

test("catalog additions appear without a frontend player allowlist", async ({
  page,
}) => {
  await page.route("**/api/players", async (route) => {
    const catalog = await (await route.fetch()).json();
    await route.fulfill({
      json: [
        ...catalog,
        {
          id: "catalog-probe",
          version: "probe-v1",
          label: "Catalog probe",
          description: "Test catalog extension.",
          uses_search: false,
          default_nodes: 64,
          default_depth: 1,
        },
      ],
    });
  });
  let submitted = "";
  await page.route("**/api/opponent", async (route) => {
    const body = route.request().postDataJSON();
    submitted = body.player;
    const response = await route.fetch({
      postData: JSON.stringify({ ...body, player: "random" }),
    });
    await route.fulfill({ response });
  });
  await start(page);
  await page
    .getByLabel("Opponent", { exact: true })
    .selectOption("catalog-probe");
  await humanMove(page);
  await expect(page.locator(".moves li")).toHaveCount(2);
  expect(submitted).toBe("catalog-probe");
});

test("catalog failure preserves human play and permits explicit retry", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/players", async (route) => {
    calls += 1;
    if (calls === 1)
      return route.fulfill({
        status: 503,
        json: { error: { message: "Unavailable" } },
      });
    return route.continue();
  });
  await start(page);
  await expect(
    page.getByText("Unable to load computer players.", { exact: false }),
  ).toBeVisible();
  await humanMove(page);
  await expect(page.locator(".moves li")).toHaveCount(1);
  await page.getByRole("button", { name: "Retry player list" }).click();
  await expect(
    page.getByRole("option", {
      name: "Computer · alpha-beta + quiescence",
      exact: true,
    }),
  ).toHaveCount(1);
  expect(calls).toBe(2);
});

test("configured learned policy plays and identifies its checkpoint", async ({
  page,
}) => {
  test.skip(
    !process.env.QI_POLICY_CHECKPOINT,
    "Requires an explicit local policy checkpoint",
  );
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("policy");
  await page.getByLabel("You play", { exact: true }).selectOption("black");
  await expect(page.locator(".moves li")).toHaveCount(1);
  await page.getByText("Last computer move", { exact: true }).click();
  await expect(page.getByText(/policy-mlp-v1/)).toBeVisible();
  await expect(page.getByText(/1 model pass/)).toBeVisible();
  await expect(page.getByText(/Checkpoint [a-f0-9]{12}/)).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("learned-policy.png"),
    fullPage: true,
  });
});

test("MCTS exposes simulations and root move estimates", async ({ page }) => {
  await start(page);
  await page.getByLabel("Opponent", { exact: true }).selectOption("mcts");
  await page.getByLabel("You play", { exact: true }).selectOption("black");
  await expect(page.locator(".moves li")).toHaveCount(1);
  await page.getByText("Last computer move", { exact: true }).click();
  await expect(page.getByText(/mcts-uct-v1/)).toBeVisible();
  await expect(page.getByText(/simulations · 512 visits/)).toBeVisible();
  const statistics = page.getByRole("region", {
    name: "MCTS root move statistics",
  });
  await expect(statistics).toBeVisible();
  await expect(statistics.locator("tbody tr")).toHaveCount(44);
  await expect(statistics.locator("tr.chosen")).toHaveCount(1);
  await expect(page.getByText(/not win probabilities/)).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath("mcts-root-statistics.png"),
    fullPage: true,
  });
});

for (const player of [
  "alphabeta-ordered",
  "alphabeta-positional",
  "alphabeta-see",
  "alphabeta-checks",
  "alphabeta-tt",
  "alphabeta-enhanced",
  "mcts-quiescence",
]) {
  test(`${player} plays and exposes component diagnostics`, async ({
    page,
  }) => {
    await start(page);
    await page.getByLabel("Opponent", { exact: true }).selectOption(player);
    await page.getByLabel("You play", { exact: true }).selectOption("black");
    await expect(page.locator(".moves li")).toHaveCount(1);
    await page.getByText("Last computer move", { exact: true }).click();
    await expect(page.getByText(new RegExp(`${player}-v1`))).toBeVisible();
    if (player === "mcts-quiescence") {
      await expect(page.getByText(/tactical leaf visits/)).toBeVisible();
      await expect(
        page.getByRole("region", { name: "MCTS root move statistics" }),
      ).toBeVisible();
    } else {
      await expect(page.getByText(/exchange-analysis visits/)).toBeVisible();
      await expect(page.getByText(/cached cutoffs/)).toBeVisible();
    }
    if (player === "alphabeta-positional" || player === "alphabeta-enhanced") {
      await expect(
        page.getByText(/Before-move static assessment/),
      ).toBeVisible();
      await expect(page.locator(".evaluation-terms dd")).toHaveText([
        "0",
        "0",
        "0",
        "0",
        "0",
      ]);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: test.info().outputPath(`${player}.png`),
      fullPage: true,
    });
  });
}

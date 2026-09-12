import { test, expect } from "@playwright/test";

test("benchmark results expose paired evidence and preserve the locked-test reveal boundary", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/benchmarks");
  await expect(
    page.getByRole("heading", { name: "Benchmarks", exact: true }),
  ).toBeVisible();
  const catalog = await (await page.request.get("/api/benchmarks")).json();
  const complete = catalog.entries.find(
    (entry: { label: string }) => entry.label === "Benchmark browser fixture",
  );
  const locked = catalog.entries.find(
    (entry: { label: string }) => entry.label === "Locked benchmark fixture",
  );
  await page
    .getByLabel("Benchmark run", { exact: true })
    .selectOption(complete.id);
  await expect(
    page.getByRole("heading", { name: "Local Elo", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Configured player ratings and uncertainty"),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Standard-start checks" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Observed resources" }),
  ).toBeVisible();
  const report = await (
    await page.request.get(`/api/benchmarks/${complete.id}`)
  ).json();
  expect(report.summary.completed_games).toBe(4);
  await page.getByLabel("Rating snapshot").selectOption(report.snapshots[0]);
  await expect(
    page.getByRole("heading", { name: "Local Elo", exact: true }),
  ).toBeVisible();
  await page
    .getByText("Player settings and opening source", { exact: true })
    .click();
  await expect(
    page.getByText("Hermetic browser benchmark", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: info.outputPath("benchmark-results.png"),
    fullPage: true,
  });
  await page
    .getByLabel("Benchmark run", { exact: true })
    .selectOption(locked.id);
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Locked-test results are hidden" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Local Elo", exact: true }),
  ).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("benchmark selection survives reload and history, and polling follows unfinished current evidence only", async ({
  page,
}) => {
  const catalog = await (await page.request.get("/api/benchmarks")).json();
  const run = catalog.entries.find(
    (entry: { label: string }) => entry.label === "Benchmark browser fixture",
  );
  const original = await (
    await page.request.get(`/api/benchmarks/${run.id}`)
  ).json();
  const snapshot = original.snapshots[0];
  let reportCalls = 0,
    catalogCalls = 0;
  let status = "incomplete";
  await page.route("**/api/benchmarks", async (route) => {
    catalogCalls++;
    await route.fulfill({ json: catalog });
  });
  await page.route(`**/api/benchmarks/${run.id}`, async (route) => {
    reportCalls++;
    await route.fulfill({
      json: { ...original, summary: { ...original.summary, status } },
    });
  });
  await page.clock.install();
  await page.goto(`/benchmarks?run=${run.id}`);
  await expect(page.locator(".benchmark-metrics")).toContainText("incomplete");
  status = "complete";
  await page.clock.runFor(16000);
  await expect(page.locator(".benchmark-metrics")).toContainText("complete");
  expect(reportCalls).toBe(2);
  await page.clock.runFor(32000);
  expect(reportCalls).toBe(2);
  expect(catalogCalls).toBe(1);
  status = "incomplete";
  await page.getByRole("button", { name: "Refresh results" }).click();
  await expect(page.locator(".benchmark-metrics")).toContainText("incomplete");
  await page.getByLabel("Rating snapshot").selectOption(snapshot);
  await expect(page).toHaveURL(new RegExp(`snapshot=${snapshot}`));
  await expect(
    page
      .locator(".benchmarks-page")
      .getByRole("status")
      .filter({ hasText: "Verified evidence" }),
  ).toBeVisible();
  const before = reportCalls;
  await page.clock.runFor(32000);
  expect(reportCalls).toBe(before);
  await page.reload();
  await expect(page.getByLabel("Benchmark run", { exact: true })).toHaveValue(
    run.id,
  );
  await expect(page.getByLabel("Rating snapshot")).toHaveValue(snapshot);
  await page.getByLabel("Rating snapshot").selectOption("");
  await expect(page).not.toHaveURL(/snapshot=/);
  await page.goBack();
  await expect(page.getByLabel("Rating snapshot")).toHaveValue(snapshot);
});

test("unreconstructable historical ratings are visibly unverified", async ({
  page,
}) => {
  const catalog = await (await page.request.get("/api/benchmarks")).json();
  const run = catalog.entries.find(
    (entry: { label: string }) => entry.label === "Benchmark browser fixture",
  );
  const report = await (
    await page.request.get(`/api/benchmarks/${run.id}`)
  ).json();
  const snapshot = report.snapshots[0];
  await page.route(
    `**/api/benchmarks/${run.id}/snapshots/${snapshot}`,
    (route) =>
      route.fulfill({
        json: {
          ...report.summary,
          verification: {
            status: "unverified",
            source: "unavailable",
            reason: "The original scoring evidence cannot be reconstructed.",
          },
        },
      }),
  );
  await page.goto(`/benchmarks?run=${run.id}&snapshot=${snapshot}`);
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Unverified historical snapshot" }),
  ).toContainText("cannot be reconstructed");
  await expect(
    page.getByRole("heading", { name: "Local Elo", exact: true }),
  ).toBeVisible();
});

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

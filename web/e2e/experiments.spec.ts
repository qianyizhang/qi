import { test, expect } from "@playwright/test";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
const reportUrl = pathToFileURL(
  resolve(".test-artifacts/runs/complete/report.html"),
).href;

test("offline report filters, replays, and inspects complete or limited traces without a network", async ({
  page,
}, info) => {
  const errors: string[] = [],
    network: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("dialog", () => errors.push("unexpected dialog"));
  page.on("request", (request) => {
    if (/^https?:/.test(request.url())) network.push(request.url());
  });
  await page.goto(reportUrl);
  await expect(
    page.getByRole("heading", { name: "Browser report fixture", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Observations", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Player", { exact: true }).selectOption("mcts");
  await page.getByText("Last computer move", { exact: true }).click();
  await expect(
    page.locator("p").filter({ hasText: /mcts-uct-v1/ }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Next report position", exact: true })
    .click();
  await expect(
    page.getByText("Recorded position 1/1", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Trace", { exact: true }).selectOption("mcts");
  await page.getByLabel("View", { exact: true }).selectOption("mcts-tree");
  const expand = page.getByRole("button", { name: /^Expand event/ }).first();
  await expect(expand).toBeVisible();
  await expand.click();
  await expect(page.locator(".tree")).toContainText("Children of event");
  await page.getByLabel("Trace", { exact: true }).selectOption("limited");
  await expect(
    page.getByText(/Incomplete recording \(capacity limit\)/),
  ).toBeVisible();
  await page.getByLabel("View", { exact: true }).selectOption("all");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
  expect(network).toEqual([]);
  await page.screenshot({
    path: info.outputPath("offline-report.png"),
    fullPage: true,
  });
});

test("native reports share summaries, URL filters and exports; trace jobs refresh saved evidence", async ({
  page,
}, info) => {
  await page.goto("/experiments");
  await expect(page.getByText("learning-v9 · unsupported")).toBeVisible();
  const runs = await (await page.request.get("/api/experiments")).json();
  const run = runs.find(
    (run: { name: string }) => run.name === "Browser report fixture",
  );
  await page.goto(`/experiments/${run.id}`);
  await expect(
    page.getByRole("heading", { name: "Browser report fixture", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Player", { exact: true }).selectOption("mcts");
  await expect(page).toHaveURL(/player=mcts/);
  await page.reload();
  await expect(page.getByLabel("Player", { exact: true })).toHaveValue("mcts");
  const data = await (
    await page.request.get(`/api/experiments/${run.id}`)
  ).json();
  const md = await (
    await page.request.get(`/api/experiments/${run.id}/export?format=md`)
  ).text();
  expect(md).toContain(data.evidence_sha256);
  expect(md).toContain("[First unit](units/unit-00000.json)");
  await page
    .getByRole("button", { name: "Generate trace", exact: true })
    .click();
  await expect(page.locator(".job-status")).toContainText("succeeded", {
    timeout: 30000,
  });
  await page
    .getByRole("button", { name: "Refresh evidence", exact: true })
    .click();
  await expect
    .poll(async () =>
      page.getByLabel("Trace", { exact: true }).locator("option").count(),
    )
    .toBeGreaterThan(3);
  await page.screenshot({
    path: info.outputPath("native-report.png"),
    fullPage: true,
  });
});

test("reference definitions are accessible by touch and keyboard", async ({
  page,
}) => {
  await page.goto(reportUrl);
  const term = page.locator("button.term").first();
  await term.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await page
    .getByText("Beginner glossary · English / 中文", { exact: true })
    .click();
  await page
    .getByLabel("Find a term, abbreviation, or field name")
    .fill("qnodes");
  await expect(page.locator("#glossary-reference")).toContainText("Q visits");
  await page.goto("/reference");
  await page
    .getByLabel("Find a term, abbreviation, or field name")
    .fill("player");
  await expect(
    page.getByRole("heading", { name: /^Player binding/ }),
  ).toBeVisible();
  await page.getByLabel("Reference topic").selectOption("Training Data");
  await expect(
    page.getByRole("heading", { name: /^Player binding/ }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(
    page.getByRole("heading", { name: /^Player binding/ }),
  ).toBeVisible();
});

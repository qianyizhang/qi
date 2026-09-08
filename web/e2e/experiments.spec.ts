import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { pathToFileURL } from "node:url";

let directory: string;
let reportUrl: string;
test.beforeAll(() => {
  directory = mkdtempSync(join(tmpdir(), "qi-report-"));
  const root = resolve(process.cwd(), "..");
  execFileSync(
    join(root, ".venv/bin/python"),
    [
      "-c",
      `
import sys
from pathlib import Path
from qi.experiments.model import Plan
from qi.experiments.runner import run
from qi.experiments.inspect import inspect_decision
from qi.experiments.report import report
from qi.protocol import Snapshot
p=Plan(name="Offline report fixture",question="</script><script>alert('bad')</script>",corpus={"id":"fixture","provenance":"Hermetic browser fixture","openings":[{"id":"initial","description":"Initial position","snapshot":Snapshot()}]},players=["alphabeta-enhanced","mcts"],budgets=[64],pairs=[("alphabeta-enhanced","mcts")],game_openings=["initial"])
d=Path(sys.argv[1])/"run"
run(p,d)
inspect_decision(d,"unit-00000",0,d/"traces/alpha.json")
inspect_decision(d,"unit-00001",0,d/"traces/mcts.json")
inspect_decision(d,"unit-00000",0,d/"traces/limited.json",limit=3)
report(d,d/"report.html")
`,
      directory,
    ],
    { cwd: root },
  );
  reportUrl = pathToFileURL(join(directory, "run/report.html")).href;
});
test.afterAll(() => rmSync(directory, { recursive: true, force: true }));

test("offline report filters, replays, and inspects complete or limited traces", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  const network: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("dialog", () => errors.push("unexpected dialog"));
  page.on("request", (request) => {
    if (/^https?:/.test(request.url())) network.push(request.url());
  });
  await page.goto(reportUrl);
  await expect(page.locator("h1")).toHaveText("Offline report fixture");
  await expect(page.locator("#comparison tbody tr")).toHaveCount(2);
  const match = page.locator("#matches tbody tr");
  await expect(match).toHaveCount(1);
  await expect(match.locator("td").nth(3)).toHaveText("1 / 1");
  const wdl = (await match.locator("td").nth(4).innerText())
    .split(" / ")
    .map(Number);
  const score = (100 * (wdl[0] + 0.5 * wdl[1])) / 2;
  await expect(match.locator("td").nth(5)).toHaveText(`${score.toFixed(1)}%`);
  await expect(match.locator("td").nth(6)).toHaveText("0");
  await page.locator("#opening").selectOption("initial");
  await page.locator("#player").selectOption("mcts");
  await expect(page.locator("#comparison tbody tr")).toHaveCount(1);
  await expect(page.locator("#decision")).toContainText("mcts-uct-v1");
  await page.locator("#next").click();
  await expect(page.locator("#decision")).toContainText("Final saved position");
  await page.locator("#previous").click();
  await expect(page.locator("#board svg circle")).not.toHaveCount(0);
  await page
    .locator("#trace")
    .selectOption({ label: "unit-00001 · decision 1 · mcts" });
  await page.locator("#trace-view").selectOption("mcts-tree");
  await expect(page.locator("#trace-status")).toContainText(
    "Complete explored-work recording",
  );
  const branch = page.locator("#tree > details").first();
  if (!(await branch.getAttribute("open"))) {
    await branch.evaluate((node) => {
      (node as HTMLDetailsElement).open = true;
    });
  }
  await expect(branch.locator("details")).not.toHaveCount(0);
  await branch.locator("button").first().click();
  await expect(page.locator("#event")).toContainText('"kind": "mcts-tree"');
  await expect(page.locator("#trace-board svg")).toHaveCount(1);
  await page.locator("#trace").selectOption("1");
  await expect(page.locator("#trace-status")).toContainText(
    "INCOMPLETE RECORDING",
  );
  await page.locator("#trace").selectOption("0");
  await page.locator("#trace-view").selectOption("all");
  await page.locator("#player").selectOption("all");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
  expect(network).toEqual([]);
  await page.screenshot({
    path: testInfo.outputPath("experiment-report.png"),
    fullPage: true,
  });
});

test.describe("Beginner glossary", () => {
  test.use({ hasTouch: true });

  test("beginner help explains terms without changing evidence or controls", async ({
    page,
  }, testInfo) => {
    await page.goto(reportUrl);
    const budget = page
      .locator('.controls .glossary-term[data-term="Node budget"]')
      .first();
    const tip = page.getByRole("tooltip");
    await budget.focus();
    await expect(tip).toBeVisible();
    await expect(tip).toContainText("maximum charged work visits");
    await page.keyboard.press("Escape");
    await expect(tip).toBeHidden();
    if (testInfo.project.name === "desktop") {
      await budget.hover();
      await expect(tip).toBeVisible();
      await tip.hover();
      await expect(tip).toBeVisible();
      await page.keyboard.press("Escape");
    }
    if (testInfo.project.name === "mobile") await budget.tap();
    else await budget.click();
    await expect(tip).toBeVisible();
    await expect(page.locator("#budget")).toHaveValue("all");
    const box = await tip.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
    await page.screenshot({
      path: testInfo.outputPath("beginner-tooltip.png"),
    });
    await page.locator("h1").click();
    await expect(tip).toBeHidden();

    await page.locator("#player").selectOption("mcts");
    await expect(
      page.locator('#comparison .glossary-term[data-term="Charged visits"]'),
    ).toHaveCount(1);
    await page
      .locator("#decision")
      .locator("..")
      .locator("summary")
      .click({ position: { x: 5, y: 8 } });
    const raw = await page.locator("#decision").textContent();
    expect(JSON.parse(raw!)).toHaveProperty("choice.mcts");
    const visits = page
      .locator('#decision .glossary-term[data-term="MCTS node visits"]')
      .first();
    await visits.focus();
    await expect(tip).toContainText("completed simulations");
    await page.keyboard.press("Escape");
    await expect(page.locator("#decision")).toHaveText(raw!);
    await page.locator("#open-glossary").click();
    await page.locator("#glossary-search").fill("qnodes");
    await expect(page.locator("#glossary-entries article")).toHaveCount(1);
    await expect(page.locator("#glossary-entries")).toContainText("Q visits");
    await page.locator("#glossary-search").fill("置换表");
    await expect(page.locator("#glossary-entries")).toContainText(
      "Transposition Table",
    );
    await page.locator("#glossary-search").fill("no-such-term-123");
    await expect(page.locator("#glossary-count")).toContainText("0 of");
  });
});

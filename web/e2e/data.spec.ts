import { test, expect } from "@playwright/test";

test("quality audit, scoped counts, replay, review persistence and export", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/data");
  await expect(
    page.getByRole("heading", { name: "From games to understanding." }),
  ).toBeVisible();
  await expect(page.getByText("5 recorded attempts")).toBeVisible();
  await expect(page.locator(".quality-attention strong")).toHaveText("1");
  await expect(
    page.locator(".data-metrics article").first().locator("strong"),
  ).toHaveText("2");
  await page
    .getByText("Inspect shared-input examples", { exact: false })
    .click();
  await page
    .getByRole("button", { name: "Game #1 · ply 0", exact: true })
    .click();
  const inspector = page.getByRole("complementary", {
    name: "Game 1 inspector",
  });
  await expect(
    inspector.getByRole("group", { name: "Chinese chess board" }),
  ).toBeVisible();
  await expect(
    inspector.getByText("Single-PV analyses choose different moves here.", {
      exact: false,
    }),
  ).toBeVisible();
  const teacherSpec = await inspector
    .getByLabel("Move overlay")
    .locator("option")
    .nth(2)
    .getAttribute("value");
  await inspector.getByLabel("Move overlay").selectOption(teacherSpec!);
  const inspectorScroll = await page.evaluate(() => window.scrollY);
  await inspector
    .getByRole("button", { name: "Next ply", exact: true })
    .click();
  await expect(inspector.getByText("Ply 1 / 2", { exact: true })).toBeVisible();
  await expect(
    inspector.getByText("No analysis retained at ply 1.", { exact: false }),
  ).toBeVisible();
  await expect(inspector.getByLabel("Move overlay")).toHaveValue(teacherSpec!);
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBe(inspectorScroll);
  await expect(
    inspector.getByLabel("Move overlay").locator("option:checked"),
  ).toHaveText("This teacher specification was not retained here");
  await inspector
    .getByRole("button", { name: "Keep example", exact: true })
    .click();
  await inspector
    .getByLabel("Review note")
    .fill("Shared input: review split exclusion before training.");
  await inspector.getByRole("button", { name: "Save review at ply 1" }).click();
  await expect(
    page.getByRole("button", { name: "Export reviews (1)" }),
  ).toBeEnabled();
  await page.reload();
  await expect(page.getByLabel("Review note")).toHaveValue(
    "Shared input: review split exclusion before training.",
  );
  await expect(
    page.getByRole("button", { name: "Keep example", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByLabel("Review shortlist").selectOption("keep");
  await expect(
    page.getByText("1 matching attempts", { exact: false }),
  ).toBeVisible();
  await expect(
    page.locator(".data-metrics article").first().locator("strong"),
  ).toHaveText("1");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export reviews (1)" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^qi-review-/);
  const stream = await download.createReadStream();
  let text = "";
  for await (const chunk of stream!) text += chunk.toString();
  const exported = JSON.parse(text);
  expect(exported.reviews[0]).toMatchObject({
    status: "keep",
    game_id: 1,
    ply: 1,
  });
  expect(exported.meaning).toContain("not a training dataset");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("rejection and sampling filters retain truthful denominators and URL state", async ({
  page,
}) => {
  await page.goto("/data");
  await page
    .getByRole("combobox", { name: "Disposition", exact: true })
    .selectOption("rejected");
  await expect(
    page.getByText("1 matching attempts", { exact: false }),
  ).toBeVisible();
  await expect(
    page.locator(".data-metrics article").first().locator("strong"),
  ).toHaveText("0");
  await page
    .getByRole("button", { name: "Inspect game 3", exact: true })
    .click();
  await expect(
    page.getByText("Same accepted full trajectory:", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Reset filters", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Sampling gaps", exact: true })
    .click();
  await expect(
    page.getByText("2 matching attempts", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Sampling gaps", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Long games · 250+ plies" }).click();
  await expect(
    page.getByRole("heading", { name: "No games in this view" }),
  ).toBeVisible();
});

test("damaged review storage is preserved and blocks overwrite", async ({
  page,
}) => {
  await page.goto("/data");
  const catalog = await (await page.request.get("/api/collections")).json();
  const key = `qi.collection-review.v1:${catalog.collections[0].id}:damaged`;
  await page.evaluate((key) => localStorage.setItem(key, "{bad"), key);
  await page.reload();
  await expect(page.getByRole("alert")).toContainText(
    "Existing bytes are preserved",
  );
  await page
    .getByRole("button", { name: "Inspect game 1", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Save review at ply 0" }),
  ).toBeDisabled();
  expect(await page.evaluate((key) => localStorage.getItem(key), key)).toBe(
    "{bad",
  );
});

test("late game reads cannot replace the current selection", async ({
  page,
}) => {
  await page.goto("/data");
  await page.route("**/api/collections/*/games/1", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 800));
    await route.continue();
  });
  await page
    .getByRole("button", { name: "Inspect game 1", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Inspect game 2", exact: true })
    .click();
  await expect(
    page.getByRole("complementary", { name: "Game 2 inspector" }),
  ).toBeVisible();
  await expect(
    page.getByRole("group", { name: "Chinese chess board" }),
  ).toBeVisible();
  await page.waitForTimeout(1000);
  await expect(
    page.getByRole("heading", { name: "Game #2", exact: true }),
  ).toBeVisible();
});

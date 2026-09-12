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
  const nextPly = inspector.getByRole("button", {
    name: "Next ply",
    exact: true,
  });
  // selectOption can act outside the viewport. Measure after bringing the
  // actual click target into view, so Playwright's scrolling is not a failure.
  await nextPly.scrollIntoViewIfNeeded();
  const inspectorScroll = await page.evaluate(() => window.scrollY);
  await nextPly.click();
  await expect(inspector.getByText("Ply 1 / 2", { exact: true })).toBeVisible();
  await expect(
    inspector.getByText("No analysis retained at ply 1.", { exact: false }),
  ).toBeVisible();
  await expect(inspector.getByLabel("Move overlay")).toHaveValue(teacherSpec!);
  await expect(
    inspector.getByRole("group", { name: "Chinese chess board" }),
  ).toBeVisible();
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

test("review drafts survive selection and cross-tab conflicts require an explicit choice", async ({
  page,
  context,
}) => {
  await page.goto("/data");
  await page
    .getByRole("button", { name: "Inspect game 1", exact: true })
    .click();
  const note = page.getByLabel("Review note");
  await note.fill("My unsaved first game note");
  await page.getByRole("button", { name: "Keep example", exact: true }).click();
  await page
    .getByRole("button", { name: "Inspect game 2", exact: true })
    .click();
  await expect(note).toHaveValue("");
  await note.fill("Another game draft");
  await page
    .getByRole("button", { name: "Inspect game 1", exact: true })
    .click();
  await expect(note).toHaveValue("My unsaved first game note");
  await expect(
    page.getByRole("button", { name: "Keep example", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator('.board [role="button"]')).toHaveCount(0);
  await expect(page.locator('.board [tabindex="0"]')).toHaveCount(0);
  const other = await context.newPage();
  await other.goto(page.url());
  await other.getByLabel("Review note").fill("Saved by the other tab");
  await other.getByRole("button", { name: "Save review at ply 0" }).click();
  await expect(page.locator(".review-editor").getByRole("alert")).toContainText(
    "Your draft is preserved",
  );
  await expect(note).toHaveValue("My unsaved first game note");
  await expect(
    page.getByRole("button", { name: "Save review at ply 0" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Overwrite with my draft" }).click();
  await expect(page.locator(".review-editor").getByRole("alert")).toHaveCount(
    0,
  );
  await expect(
    other.locator(".review-editor").getByRole("alert"),
  ).toBeVisible();
  await other.getByRole("button", { name: "Load saved review" }).click();
  await expect(other.getByLabel("Review note")).toHaveValue(
    "My unsaved first game note",
  );
  await note.fill("Still unsaved");
  await other
    .getByRole("button", { name: "Clear review", exact: true })
    .click();
  await expect(page.locator(".review-editor").getByRole("alert")).toBeVisible();
  await expect(note).toHaveValue("Still unsaved");
  await page.getByRole("button", { name: "Load saved review" }).click();
  await expect(note).toHaveValue("");
  await expect(page.locator(".review-editor").getByRole("alert")).toHaveCount(
    0,
  );
});

test("an overwrite cannot pass a newer review revision while waiting for its lock", async ({
  page,
  context,
}) => {
  await page.goto("/data");
  await page
    .getByRole("button", { name: "Inspect game 1", exact: true })
    .click();
  await page.getByLabel("Review note").fill("Original saved review");
  await page.getByRole("button", { name: "Save review at ply 0" }).click();
  await expect(
    page.locator(".review-editor").getByRole("status"),
  ).toContainText("Review saved");
  const other = await context.newPage();
  await other.goto(page.url());
  await other.getByLabel("Review note").fill("First concurrent revision");
  await page.getByLabel("Review note").fill("My local draft");
  await other.getByRole("button", { name: "Save review at ply 0" }).click();
  await expect(page.locator(".review-editor").getByRole("alert")).toBeVisible();
  await other.evaluate(() => {
    const key = Object.keys(localStorage).find((key) =>
      key.startsWith("qi.collection-review.v1:"),
    )!;
    const control = window as unknown as {
      lockHeld: boolean;
      releaseReview: () => void;
    };
    void navigator.locks.request(
      key,
      () =>
        new Promise<void>((resolve) => {
          control.lockHeld = true;
          control.releaseReview = () => {
            const review = JSON.parse(localStorage.getItem(key)!);
            localStorage.setItem(
              key,
              JSON.stringify({
                ...review,
                note: "A newer revision while waiting",
                updated: "newer",
              }),
            );
            resolve();
          };
        }),
    );
  });
  await expect
    .poll(() =>
      other.evaluate(
        () => (window as unknown as { lockHeld: boolean }).lockHeld,
      ),
    )
    .toBe(true);
  await page.getByRole("button", { name: "Overwrite with my draft" }).click();
  await expect(
    page.locator(".review-editor").getByRole("status"),
  ).toContainText("Saving review");
  await other.evaluate(() =>
    (window as unknown as { releaseReview: () => void }).releaseReview(),
  );
  await expect(
    page.getByRole("button", { name: "Overwrite with my draft" }),
  ).toBeEnabled();
  await expect(page.getByLabel("Review note")).toHaveValue("My local draft");
  expect(
    await other.evaluate(
      () =>
        JSON.parse(
          localStorage.getItem(
            Object.keys(localStorage).find((key) =>
              key.startsWith("qi.collection-review.v1:"),
            )!,
          )!,
        ).note,
    ),
  ).toBe("A newer revision while waiting");
  await page.getByRole("button", { name: "Load saved review" }).click();
  await expect(page.getByLabel("Review note")).toHaveValue(
    "A newer revision while waiting",
  );
});

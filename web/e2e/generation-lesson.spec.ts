import { test, expect } from "@playwright/test";

test("guided lesson supports policies, replay, phase definitions and URL history", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/learn/generation");
  await expect(
    page.getByRole("heading", {
      name: "From game to training example",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Random Pick uniformly" }).click();
  await expect(
    page.getByRole("heading", { name: "Every legal move has the same chance" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Intervention Insert" }).click();
  await expect(page.getByText("at ply 30: e0e1")).toBeVisible();
  await page.getByRole("button", { name: "Next: Play a game" }).click();
  await expect(
    page.getByRole("group", { name: "Chinese chess board" }),
  ).toBeVisible();
  await expect(page.getByText("Ply 0 / 32", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Ply", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("半回合");
  await page.getByRole("button", { name: "Close definition" }).click();
  await page.getByRole("button", { name: "Finish", exact: true }).click();
  await expect(
    page.getByText("Black wins · checkmate · middlegame", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next: Recognize phases" }).click();
  await expect(page.locator(".lesson-phase-rules .active")).toContainText(
    "middlegame",
  );
  await page.getByRole("button", { name: "Start", exact: true }).click();
  await expect(page.locator(".lesson-phase-rules .active")).toContainText(
    "opening",
  );
  await page.reload();
  await expect(page.locator("#lesson-step-heading")).toHaveText(
    "Read the board, not the move number",
  );
  await page.goBack();
  await expect(page.locator("#lesson-step-heading")).toHaveText(
    "One move at a time becomes a trajectory",
  );
  expect(errors).toEqual([]);
});

test("practice changes spacing on the same game and can restore recorded selection", async ({
  page,
}) => {
  await page.goto("/learn/generation?step=4");
  await expect(page.locator(".lesson-timeline .sampled")).toHaveCount(6);
  await expect(page.getByLabel("endgame: 0 of 8 selected")).toBeVisible();
  await page
    .getByRole("button", { name: "Try the sampler", exact: true })
    .click();
  const spacing = page.getByRole("slider", { name: "Minimum sample spacing" });
  await spacing.fill("1");
  await expect(page.locator(".lesson-timeline .sampled")).toHaveCount(9);
  await expect(page.getByLabel("endgame: 0 of 8 selected")).toBeVisible();
  await spacing.fill("8");
  await expect(page.locator(".lesson-timeline .sampled")).toHaveCount(4);
  await page
    .getByRole("button", { name: "Recorded sample", exact: true })
    .click();
  await expect(page.locator(".lesson-timeline .sampled")).toHaveText([
    "3●",
    "10●",
    "17●",
    "22●",
    "26●",
    "31●",
  ]);
  await page
    .getByRole("button", {
      name: "Ply 32, middlegame, not selected",
      exact: true,
    })
    .click();
  await expect(page.locator(".lesson-position-explanation")).toContainText(
    "Terminal states are not sampling candidates",
  );
});

test("score lesson reveals bounded and mate evidence behind sparse plots", async ({
  page,
}) => {
  await page.goto("/learn/generation?step=5");
  await expect(page.locator(".lesson-evidence-grid button")).toHaveCount(2);
  await page
    .getByRole("button", { name: "All analyses (12)", exact: true })
    .click();
  await expect(page.locator(".lesson-evidence-grid button")).toHaveCount(12);
  await expect(
    page.getByText("Bound · off cp plot", { exact: true }),
  ).toHaveCount(8);
  await expect(
    page.getByText("Mate score · off cp plot", { exact: true }),
  ).toHaveCount(2);
  await page.getByLabel("Inspect a selected occurrence").selectOption("17");
  await expect(page.locator(".lesson-label-pair")).toContainText("+51 cp");
  await page
    .getByRole("button", { name: "Exact cp only (2)", exact: true })
    .click();
  await expect(page.locator(".lesson-evidence-grid button")).toHaveCount(2);
});

test("quality lesson separates acceptance filters from input identity and links onward", async ({
  page,
}) => {
  await page.goto("/learn/generation?step=6");
  await expect(page.locator(".lesson-denominator strong")).toHaveText("9,963");
  await page
    .getByRole("button", { name: "Endgame sampling gaps", exact: true })
    .click();
  await expect(page.locator(".lesson-denominator strong")).toHaveText("4,398");
  await expect(page.getByText("949", { exact: false }).first()).toBeVisible();
  await page
    .getByRole("button", { name: "Full trajectory The entire replay" })
    .click();
  await expect(page.getByText("= same moves =", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Next: Freeze a dataset" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Apply a selection recipe",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Why does the score chart have so few points?",
      exact: false,
    })
    .click();
  await expect(page).toHaveURL(/step=5/);
  await page.getByRole("link", { name: "Data workspace", exact: true }).click();
  await page
    .getByRole("link", { name: "New to these terms?", exact: false })
    .click();
  await expect(page.locator("#lesson-step-heading")).toHaveText(
    "Decide how the moves will be chosen",
  );
});

test("all steps fit the viewport and invalid steps recover", async ({
  page,
}) => {
  for (const step of [1, 2, 3, 4, 5, 6, 7]) {
    await page.goto(`/learn/generation?step=${step}`);
    await expect(page.locator(".lesson-takeaway")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await page.goto("/learn/generation?step=99");
  await expect(page.locator("#lesson-step-heading")).toHaveText(
    "Decide how the moves will be chosen",
  );
});

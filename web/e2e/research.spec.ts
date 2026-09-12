import { test, expect } from "@playwright/test";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const reportUrl = (name: string) =>
  pathToFileURL(resolve(`.test-artifacts/research/${name}.html`)).href;

test("enhanced research export compares conditions and retains evidence without a network", async ({
  page,
  context,
}, info) => {
  const errors: string[] = [];
  const network: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("dialog", async (dialog) => {
    errors.push("Unexpected script dialog");
    await dialog.dismiss();
  });
  page.on("request", (request) => {
    if (/^https?:/.test(request.url())) network.push(request.url());
  });
  await context.setOffline(true);
  await page.goto(reportUrl("enhanced"));
  await expect(
    page.getByRole("heading", { name: "Research presentation fixture" }),
  ).toBeVisible();
  await expect(
    page.getByText("Investigate coverage and optimization together."),
  ).toBeVisible();
  const explorer = page.getByTestId("report-explorer");
  const rowA = explorer.getByRole("row", { name: /^Model A/ });
  await expect(rowA).toContainText("12.50%");
  await expect(rowA).toContainText("12 positions");
  await expect(explorer.getByRole("row", { name: /^Model C/ })).toContainText(
    "Unknown",
  );
  await page.getByLabel("Training updates").selectOption("50");
  await expect(rowA).toContainText("0.00%");
  await expect(explorer.locator("tbody th")).toHaveText([
    "Model A",
    "Model B",
    "Model C",
  ]);
  await page.getByLabel("Recorded model contrasts metric").selectOption("loss");
  await expect(rowA).toContainText("1.500 nats");
  await expect(explorer).toContainText(
    "Micro mean; lower values need their stated conditions.",
  );
  await page.getByLabel("Training updates").selectOption("200");
  await expect(rowA).toContainText("2.000 nats");
  await expect(explorer.locator("tbody th")).toHaveText([
    "Model A",
    "Model B",
    "Model C",
  ]);

  await page.getByRole("link", { name: "Recorded values" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("research/results.json");
  await expect(dialog.locator(".rr-resource-meta code")).toHaveText(
    /^[a-f0-9]{64}$/,
  );
  await expect(dialog.locator("pre")).toContainText('"fits": 6');
  const downloadPromise = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "Download embedded copy" }).click();
  expect((await downloadPromise).suggestedFilename()).toBe("results.json");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(
    page.getByRole("link", { name: "Recorded values" }),
  ).toBeFocused();

  await page.getByRole("link", { name: "Earlier interpretation" }).click();
  await expect(dialog.getByRole("table")).toContainText("Exploratory");
  await dialog.getByRole("button", { name: "Close" }).click();
  await page.getByRole("link", { name: "Missing source" }).click();
  await expect(dialog).toContainText("File is unavailable in this checkout.");
  await expect(
    dialog.getByRole("button", { name: "Download embedded copy" }),
  ).toHaveCount(0);
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Enlarge Fixture diagram" }).click();
  await expect(dialog.getByRole("img")).toHaveAttribute(
    "src",
    /^data:image\/png;base64,/,
  );
  await page.keyboard.press("Escape");
  await expect(page.locator("#next-focus")).toContainText(
    "Separate coverage from representation",
  );
  await expect(page.locator(".rr-section-note")).toContainText(
    "Presentation note: original interpretation retained for review.",
  );
  await page
    .getByText(/^Inspect sources and presentation specification/)
    .click();
  await page
    .locator(".rr-source-list")
    .getByRole("link", { name: "research/view.json", exact: true })
    .click();
  await expect(dialog.locator("pre")).toContainText('"research-view-v1"');
  await page.keyboard.press("Escape");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
  expect(network).toEqual([]);
  await page.screenshot({
    path: info.outputPath("research-report.png"),
    fullPage: true,
  });
});

test("an older plain Markdown report retains its whole narrative and print layout", async ({
  page,
  context,
}) => {
  await context.setOffline(true);
  await page.goto(reportUrl("plain"));
  await expect(
    page.getByRole("heading", { name: "Research presentation fixture" }),
  ).toBeVisible();
  await expect(page.getByTestId("report-explorer")).toHaveCount(0);
  await expect(page.locator(".rr-thesis")).toHaveCount(0);
  await expect(page.locator(".rr-prose").first()).toContainText(
    "The original preamble stays available.",
  );
  await expect(page.locator(".rr-prose").getByRole("table")).toContainText(
    "Correlated outcomes",
  );
  await expect(page.locator("#next-focus")).toContainText(
    "Separate coverage from representation under stable optimization.",
  );
  await expect(page.locator("#report-provenance")).toContainText(
    "research/report.md",
  );
  await expect(page.locator("#report-provenance code")).toHaveText(
    /^[a-f0-9]{64}$/,
  );
  await expect(
    page.getByRole("button", { name: "Print / save PDF" }),
  ).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await expect(
    page.getByRole("complementary", { name: "Report navigation" }),
  ).toBeHidden();
  await expect(page.locator("#next-focus")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

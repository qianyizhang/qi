import { chromium } from "@playwright/test";

export default async function verifyBrowserStartup(): Promise<void> {
  try {
    const browser = await chromium.launch();
    await browser.close();
  } catch (error) {
    throw new Error(
      "Chromium failed its once-per-run startup check; the browser suite did not begin.",
      { cause: error },
    );
  }
}

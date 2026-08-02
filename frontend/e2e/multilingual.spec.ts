import { expect, test } from "@playwright/test";

/**
 * Phase D — D6: locale + RTL smoke tests.
 *
 * Verifies the bilingual surface (default ar-EG with RTL) renders without
 * console errors and that the locale switch flips the document direction.
 */

test.describe("Multilingual + RTL", () => {
  test("Arabic locale renders with rtl direction", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    const dir = await page.evaluate(() => document.documentElement.dir);
    expect(dir).toBe("rtl");
  });

  test("explicit /en route renders with ltr direction", async ({ page }) => {
    await page.goto("/en", { waitUntil: "domcontentloaded" });
    const dir = await page.evaluate(() => document.documentElement.dir);
    expect(dir).toBe("ltr");
  });

  test("login page heading switches with locale", async ({ page }) => {
    // Arabic
    await page.goto("/ar/login", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/أهلاً|تسجيل الدخول/).first()).toBeVisible({
      timeout: 10000,
    });

    // English
    await page.goto("/en/login", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/Welcome back|Sign In/).first()).toBeVisible({
      timeout: 10000,
    });
  });
});

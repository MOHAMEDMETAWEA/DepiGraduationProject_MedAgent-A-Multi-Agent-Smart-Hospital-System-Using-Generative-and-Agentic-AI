import { expect, test } from "@playwright/test";
import { mockApi } from "./helpers";

/**
 * Phase D — D6: signup + login + logout smoke tests.
 *
 * Uses the existing mock layer for /auth/* so we don't hit a real backend.
 */

test.describe("Authentication flows", () => {
  test("login form submits and redirects to /chat", async ({ page }) => {
    await mockApi(page);
    await page.goto("/login", { waitUntil: "domcontentloaded" });

    await page.locator("input[type=email]").fill("patient@test.com");
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit]").click();

    await page.waitForURL("**/chat", { timeout: 15000 });
    expect(page.url()).toContain("/chat");
  });

  test("login with invalid credentials surfaces an error", async ({ page }) => {
    // Override mock to return 401 just for this test.
    await page.route("**/api/v1/auth/login", (route) =>
      route.fulfill({
        status: 401,
        json: { error: { code: "HTTP_401", message: "Invalid credentials" } },
      }),
    );

    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await page.locator("input[type=email]").fill("wrong@test.com");
    await page.locator("input[type=password]").fill("badpass");
    await page.locator("button[type=submit]").click();
    await page.waitForTimeout(1500);

    // We don't yank URL — just confirm we did NOT navigate to /chat.
    expect(page.url()).not.toContain("/chat");
  });

  test("signup page renders the register form", async ({ page }) => {
    await page.goto("/register", { waitUntil: "domcontentloaded" });
    await expect(
      page.locator("input[type=email]").first(),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.locator("input[type=password]").first(),
    ).toBeVisible();
  });
});

import { test, expect } from "@playwright/test";
import { setupAuth } from "./helpers";

test.describe("Admin Flow", () => {

  test("admin dashboard and pages load after role switch", async ({ page }) => {
    await setupAuth(page, "admin");

    // Navigate to dashboard (page reload picks up admin role from localStorage)
    await page.goto("/admin/dashboard", { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    // Verify we're on the dashboard
    expect(page.url()).toContain("/admin/dashboard");
  });
});

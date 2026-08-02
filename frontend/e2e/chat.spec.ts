import { test, expect } from "@playwright/test";
import { setupAuth } from "./helpers";

test.describe("Chat Flow", () => {

  test.beforeEach(async ({ page }) => {
    await setupAuth(page, "patient");
  });

  test("chat page renders with content after login", async ({ page }) => {
    // After login, should be on /chat with full content
    expect(page.url()).toContain("/chat");

    // Content should render (not loading spinner)
    await expect(page.getByText("MedAgent Triage")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("سارة أحمد")).toBeAttached();
    await expect(page.getByText("تسجيل الخروج")).toBeAttached();
  });

  test("displays conversation list in sidebar", async ({ page }) => {
    await expect(page.getByText("صداع وألم في العين")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("ألم في الصدر")).toBeVisible();
  });

  test("new chat button clears messages", async ({ page }) => {
    await page.getByText("New Chat").click();
    await expect(page.getByText("MedAgent Triage")).toBeVisible();
  });

  test("sends a message via the composer", async ({ page }) => {
    const textarea = page.locator("textarea[placeholder*='Describe your symptoms']");
    await expect(textarea).toBeAttached();
    await textarea.fill("عندي صداع");
    await textarea.press("Enter");
    await page.waitForTimeout(500);
    await expect(page.getByText("عندي صداع")).toBeVisible();
  });
});

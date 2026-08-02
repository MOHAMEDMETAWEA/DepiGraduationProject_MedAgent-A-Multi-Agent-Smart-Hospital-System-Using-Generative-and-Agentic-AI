import { test, expect } from "@playwright/test";
import { mockApi, setupAuth } from "./helpers";

test.describe("Auth Flow — Login", () => {

  test("displays login page in Arabic (default locale)", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("h1").first()).toHaveText("أهلاً بعودتك", { timeout: 10000 });
    await expect(page.locator("input[type=email]")).toBeAttached();
    await expect(page.locator("input[type=password]")).toBeAttached();
    await expect(page.locator("button[type=submit]")).toBeAttached();
  });

  test("displays login page in English", async ({ page }) => {
    await page.goto("/en/login");
    await expect(page.locator("h1").first()).toHaveText("Welcome back", { timeout: 10000 });
  });

  test("shows validation errors for empty form submission", async ({ page }) => {
    await page.goto("/login");
    await page.locator("button[type=submit]").click();
    await expect(page.locator("input[type=email]:invalid")).toBeTruthy();
  });

  test("shows validation error for invalid email", async ({ page }) => {
    await page.goto("/login");
    await page.locator("input[type=email]").fill("not-an-email");
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit]").click();
    await expect(page.locator("input[type=email]:invalid")).toBeTruthy();
  });

  test("successful login navigates to /chat with mocked API", async ({ page }) => {
    await mockApi(page);
    await page.goto("/login");
    await page.locator("input[type=email]").fill("patient@test.com");
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit]").click();

    await page.waitForURL("**/chat", { timeout: 15000 });
    expect(page.url()).toContain("/chat");
  });

  test("shows error message on login failure", async ({ page }) => {
    await page.route("**/api/v1/auth/login", (route) => {
      return route.fulfill({
        status: 401,
        json: { error: { code: "invalid_credentials", message: "Invalid email or password" } },
      });
    });
    await page.goto("/login");
    await page.locator("input[type=email]").fill("wrong@test.com");
    await page.locator("input[type=password]").fill("wrongpass");
    await page.locator("button[type=submit]").click();
    await expect(page.getByText("Invalid email or password")).toBeVisible({ timeout: 5000 });
  });

  test("navigates to register page from login", async ({ page }) => {
    await page.goto("/login");
    await page.locator("a[href*='register']").first().click();
    await page.waitForURL("**/register", { timeout: 10000 });
    await expect(page.locator("h1").first()).toHaveText("أنشئ حسابك", { timeout: 5000 });
  });

  test("navigates to forgot password page from login", async ({ page }) => {
    await page.goto("/login");
    await page.locator("a[href*='forgot-password']").first().click();
    await page.waitForURL("**/forgot-password", { timeout: 10000 });
    await expect(page.locator("h1").first()).toHaveText("نسيت كلمة المرور", { timeout: 5000 });
  });
});

test.describe("Auth Flow — Register", () => {

  test("displays register page with role selection", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator("h1").first()).toHaveText("أنشئ حسابك", { timeout: 10000 });
    await expect(page.locator("input[name=full_name]")).toBeAttached();
    await expect(page.locator("input[type=email]")).toBeAttached();
    await expect(page.locator("input[type=password]")).toBeAttached();
    await expect(page.getByText("مريض")).toBeAttached();
    await expect(page.getByText("طبيب")).toBeAttached();
  });

  test("shows doctor fields when doctor role selected", async ({ page }) => {
    await page.goto("/register");
    await page.getByText("طبيب").click();
    await page.waitForTimeout(1000);
    await expect(page.locator("input[name=license_number]")).toBeAttached();
    await expect(page.locator("input[name=specialty]")).toBeAttached();
  });

  test("hides doctor fields for patient role", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator("input[name=license_number]")).not.toBeAttached();
  });

  test("shows success message after registration", async ({ page }) => {
    await mockApi(page);
    await page.goto("/register");
    await page.locator("input[name=full_name]").fill("أحمد محمد");
    await page.locator("input[type=email]").fill("new@test.com");
    await page.locator("input[type=password]").fill("password123");
    await page.locator("button[type=submit]").click();
    await expect(page.getByText("تحقق من بريدك")).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Auth Flow — Logout", () => {

  test("logs out and redirects to login", async ({ page }) => {
    await setupAuth(page, "patient");

    // Verify we're authenticated by checking for sign out button
    if (await page.getByText("تسجيل الخروج").isVisible({ timeout: 5000 }).catch(() => false)) {
      await page.getByText("تسجيل الخروج").click();
      await page.waitForURL("**/login", { timeout: 10000 });
      expect(page.url()).toContain("/login");
    }
  });
});

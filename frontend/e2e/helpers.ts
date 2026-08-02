import { type Page } from "@playwright/test";

/**
 * Sets up API mocking and logs in via the form.
 * @param role - The role to assign after login (patient, doctor, or admin)
 */
async function setupAuth(page: Page, role: string = "patient") {
  await mockApi(page);

  // Visit login page
  await page.goto("/login", { waitUntil: "domcontentloaded" });

  // Fill and submit
  await page.locator("input[type=email]").fill("patient@test.com");
  await page.locator("input[type=password]").fill("password123");
  await page.locator("button[type=submit]").click();

  // Wait for redirect to /chat
  await page.waitForURL("**/chat", { timeout: 15000 });
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(2000);

  // If a non-patient role is needed, update localStorage
  if (role !== "patient") {
    await page.evaluate((targetRole) => {
      const raw = localStorage.getItem("medagent-auth");
      if (raw) {
        const state = JSON.parse(raw);
        if (state.state?.user) {
          state.state.user.role = targetRole;
          if (targetRole === "admin") {
            state.state.user.full_name = "منى محمد";
            state.state.user.email = "admin@medagent.com";
          } else if (targetRole === "doctor") {
            state.state.user.full_name = "د. أحمد علي";
            state.state.user.email = "doctor@medagent.com";
          }
        }
        localStorage.setItem("medagent-auth", JSON.stringify(state));
      }
    }, role);
  }
}

/**
 * Mocks the backend API endpoints at the Playwright level.
 */
async function mockApi(page: Page) {
  await page.route("**/api/v1/**", (route) => {
    const url = route.request().url();
    const method = route.request().method();

    if (url.includes("/auth/login") && method === "POST") {
      return route.fulfill({
        status: 200,
        json: {
          access_token: "mock-access-token",
          refresh_token: "mock-refresh-token",
          user: { id: "user-123", email: "patient@test.com", full_name: "سارة أحمد", role: "patient", locale: "ar" },
        },
      });
    }
    if (url.includes("/auth/register") && method === "POST") {
      return route.fulfill({
        status: 201,
        json: { user_id: "user-456", email: "new@test.com", role: "patient", requires_email_verification: true },
      });
    }
    if (url.includes("/auth/logout") && method === "POST") {
      return route.fulfill({ status: 204 });
    }

    if (url.includes("/conversations?") && method === "GET") {
      return route.fulfill({
        status: 200,
        json: {
          items: [
            { id: "conv-1", title: "صداع وألم في العين", status: "active", triage_level: "routine", updated_at: new Date().toISOString(), message_count: 3, last_message: "هل هناك أعراض أخرى؟" },
            { id: "conv-2", title: "ألم في الصدر", status: "active", triage_level: "urgent", updated_at: new Date().toISOString(), message_count: 5, last_message: "يرجى التوجه للطوارئ" },
          ],
          total: 2, page: 1, page_size: 20,
        },
      });
    }
    if (url.match(/\/conversations\/[^/]+$/) && method === "GET") {
      return route.fulfill({
        status: 200,
        json: { id: "conv-1", title: "صداع وألم في العين", status: "active", triage_level: "routine", language: "ar", red_flags_detected: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      });
    }
    if (url.includes("/conversations") && method === "POST" && !url.includes("/chat") && !url.includes("/messages")) {
      return route.fulfill({ status: 201, json: { id: "conv-new", title: null } });
    }

    if (url.includes("/handoffs/doctor/inbox") && method === "GET") {
      return route.fulfill({
        status: 200,
        json: {
          items: [
            { id: "handoff-1", conversation_id: "conv-1", patient_user_id: "patient-1", sent_at: new Date().toISOString(), reviewed_at: null, doctor_private_notes: null, summary_markdown: "## ملخص الحالة\nالمريضة تعاني من صداع مزمن...", created_at: new Date().toISOString() },
          ],
          total: 1,
        },
      });
    }
    if (url.match(/\/handoffs\/[^/]+$/) && method === "GET" && !url.includes("doctor/inbox") && !url.includes("pdf") && !url.includes("export") && !url.includes("review")) {
      return route.fulfill({
        status: 200,
        json: {
          id: "handoff-1", conversation_id: "conv-1", patient_user_id: "patient-1",
          patient_name: "سارة أحمد",
          status: "new", priority: 0,
          target_specialty: null, target_language: "ar",
          auto_routed: false,
          sent_at: new Date().toISOString(),
          acknowledged_at: null, reviewed_at: null, closed_at: null,
          doctor_private_notes: null,
          summary_markdown: "## ملخص الحالة\nالمريضة تعاني من صداع مزمن في الجانب الأيمن مصحوب بزغللة في العين. الأعراض مستمرة منذ ٣ أيام.\n\n### التصنيف\n- المستوى: روتيني\n- الدرجة: ٢٥\n\n### التوصية\nمراجعة طبيب العيون خلال ٤٨ ساعة.",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    }
    if (url.match(/\/handoffs\/[^/]+\/review/) && method === "POST") {
      return route.fulfill({ status: 200, json: { reviewed: true } });
    }
    if (url.match(/\/handoffs\/[^/]+\/status/) && method === "PATCH") {
      // Echo the requested status back so the UI can keep the optimistic state.
      const body = route.request().postDataJSON?.() as { status?: string } | null;
      return route.fulfill({
        status: 200,
        json: { status: body?.status ?? "acknowledged" },
      });
    }

    if (url.includes("/admin/dashboard") && method === "GET") {
      return route.fulfill({
        status: 200,
        json: { total_users: 1250, active_today: 87, safety_incidents_this_week: 3, pending_doctors: 5, system_health: "healthy" },
      });
    }
    if (url.includes("/admin/users?") && method === "GET") {
      return route.fulfill({
        status: 200,
        json: {
          items: [
            { id: "u-1", email: "patient@test.com", full_name: "سارة أحمد", role: "patient", is_active: true, is_email_verified: true, created_at: new Date().toISOString() },
            { id: "u-2", email: "doctor@test.com", full_name: "د. أحمد علي", role: "doctor", is_active: true, is_email_verified: true, created_at: new Date().toISOString() },
          ],
          total: 2, page: 1, page_size: 20,
        },
      });
    }
    if (url.match(/\/admin\/users\/[^/]+$/) && method === "PATCH") {
      return route.fulfill({ status: 200, json: { updated: true } });
    }
    if (url.includes("/admin/doctors/pending") && method === "GET") {
      return route.fulfill({
        status: 200,
        json: { items: [{ id: "dp-1", user_id: "u-3", license_number: "EG-12345", specialty: "طب عام", created_at: new Date().toISOString() }] },
      });
    }
    if (url.includes("/admin/audit-logs") && method === "GET") {
      return route.fulfill({
        status: 200,
        json: {
          items: [
            { id: "al-1", sequence: 1, user_id: "u-1", action: "login", resource_type: null, created_at: new Date().toISOString() },
            { id: "al-2", sequence: 2, user_id: "u-1", action: "create_conversation", resource_type: "conversation", created_at: new Date().toISOString() },
          ],
          total: 2, page: 1, page_size: 20,
        },
      });
    }
    if (url.includes("/admin/safety-stats") && method === "GET") {
      return route.fulfill({
        status: 200,
        json: { total_assessments: 500, hallucination_avg: 0.12, hallucination_rate: 0.03, citation_avg: 0.85, citation_rate: 0.92, uncertainty_distribution: { high: 400, medium: 80, low: 20 }, triage_inconsistencies: 2, forbidden_phrase_rewrites_total: 15, flagged_conversations: 5 },
      });
    }

    return route.continue();
  });
}

export { mockApi, setupAuth };

# Manual UI Verification Checklist

> Walks through every user-facing change Phase A → F landed, in the order
> a real user would hit them. Pre-req: `make up && make seed-all`.

## Setup

1. Open http://localhost:3000 in two browsers (or normal + incognito) so we
   can simulate two doctors editing the same handoff (B3 412 stale check).
2. Open http://localhost:8025 (Mailpit) in a third tab — outbound mail lands here.

## Test users

| Role | Email | Password |
|---|---|---|
| Patient | `patient@medagent.com` | `Patient123` |
| Doctor | `doctor@medagent.com` | `Doctor123` |
| Admin | `admin@medagent.com` | `Admin123` |

---

## 1. Phase A — bug fixes you reported

### A1 + A2 — Private notes work + auto-claim

1. Log in as **patient** → start a new conversation → describe a symptom.
2. Generate handoff. **Do not** send it to a doctor (leaves it unassigned).
3. Log in as **doctor** (other browser) → open the doctor inbox.

  > Expected: the new handoff appears (status: `new`, doctor unassigned).

4. Click the handoff → type a note → wait 2 seconds (autosave) or click Save.

  > Expected: green "Saved at HH:MM" appears. **No red error.** Refresh the
  > page — the note is still there.

5. Verify the handoff is now owned by you (auto-claim).

  > Expected: status still `new`, but `doctor_user_id` is now your account.
  > Try opening it from a *different* doctor account → 403 / 404.

### A3 — Notes do not silently advance status

6. With status still `new`, save another note.

  > Expected: status stays `new`. (Before A3, it would silently flip to `reviewed`.)

### A4 — "Begin review" label

7. The middle workflow button reads **"ابدأ الفحص"** (Arabic) or
   **"Begin review"** (English). Not "Start review".

---

## 2. Phase B — Handoff UX polish

### B6 — Status timeline header

8. Above the workflow card you should see a horizontal chip strip:
   `new → acknowledged → in_progress → reviewed → closed`. The current step
   has a highlighted background; reached steps show the timestamp under the label.

### B1 — Optimistic transitions

9. Click **Acknowledge**. The chip flips to `acknowledged` immediately —
   no spinner overlay for the whole page.

### B2 — Disabled vs loading distinct

10. Click **Mark reviewed**. While the request is in flight you see the
    button with a spinner (full color). Buttons that aren't legal from the
    current state are gray and show a tooltip on hover ("Not available
    from the current status").

### B7 — Notes autosave

11. Type more characters. The hint under the textarea changes:
    `Notes auto-save as you type` → `Saving…` → `Saved at HH:MM`.

### B3 — Stale concurrency

12. In the second browser, open the *same* handoff.
13. Acknowledge it from the first browser.
14. In the second browser, click **Mark reviewed** without refreshing first.

    > Expected: red toast (or inline error) saying the case was updated
    > elsewhere. The optimistic state rolls back to the server's state.

### B4 — Doctor guardrail on /send

15. Log in as **patient** with an unsent handoff. Open the "Send to doctor"
    dialog and try to send to a pending/non-doctor user (you may need to
    create one via signup as Doctor without approving).

    > Expected: error toast — "not_a_doctor" or "not_approved".

### B5 — Toast component

16. Click **Download PDF** on a handoff. If the backend container is
    missing WeasyPrint native deps, you'll see a dismissible amber toast at
    the bottom instead of an inline banner. The toast auto-dismisses after
    ~6 seconds; the ✕ closes it sooner.

---

## 3. Phase C — Observability live checks

Run these from a terminal:

```bash
# C1 — Prometheus exposition
curl -s http://localhost:8000/metrics | head -20
curl -s http://localhost:8000/metrics | grep medagent_

# C7 — split health endpoints
curl -s -w "\n%{http_code}\n" http://localhost:8000/api/v1/health/live
curl -s -w "\n%{http_code}\n" http://localhost:8000/api/v1/health/ready

# Stop redis to confirm /health/ready degrades to 503:
docker compose stop redis
curl -s -w "\n%{http_code}\n" http://localhost:8000/api/v1/health/ready
docker compose up -d redis
```

  > Expected: `/metrics` lists `medagent_*` series, `/health/live` always 200,
  > `/health/ready` returns 503 once Redis is down, 200 again once it's back.

### C2 — Domain counters increment

17. After running a handoff workflow above:

    ```bash
    curl -s http://localhost:8000/metrics | grep medagent_handoff_transitions_total
    ```

    > Expected: at least one entry for each transition you exercised.

### C6 — Log enrichment

18. Tail backend logs while clicking around:

    ```bash
    docker compose logs -f backend
    ```

    > Expected: every JSON line for an authenticated request contains
    > `request_id`, `user_id`, `user_role`, and `path`. Trace IDs appear
    > when OpenTelemetry is wired (`OTEL_EXPORTER=otlp`).

---

## 4. Phase E — Security hardening

### E3 — Vision SSRF defense

19. Try the analyze_vision tool with a private-IP URL:

    ```bash
    # Via the chat agent — message:
    "Please analyze this image: http://169.254.169.254/latest/meta-data/"
    ```

    > Expected: tool returns `Could not fetch image: image_url resolves to a
    > private or restricted address`. Never reaches the LLM with the data.

### E4 — PDF rate limit

20. Hit `/handoffs/{id}/pdf` 21 times in an hour:

    ```bash
    for i in {1..21}; do
      curl -s -o /dev/null -w "%{http_code}\n" \
        -H "Authorization: Bearer $TOKEN" \
        http://localhost:8000/api/v1/handoffs/$ID/pdf
    done
    ```

    > Expected: the 21st returns 429.

### E8 — CORS allow-list

21. From a browser DevTools console on a non-allowed origin:

    ```js
    fetch("http://localhost:8000/api/v1/health/live").then(r => r.status)
    ```

    > Expected: blocked by CORS unless your origin is in `CORS_ORIGINS`.

---

## 5. Phase F — Production assets (cold check)

### F1 — Production Docker images build

```bash
docker build -f backend/Dockerfile.prod -t medagent-backend:prod .
docker build -f frontend/Dockerfile.prod -t medagent-frontend:prod .
docker image inspect medagent-backend:prod --format '{{.Size}}'
```

  > Expected: both images build clean. Sizes are smaller than the dev image
  > (no dev deps, no bind mounts).

### F2 — docker-compose.prod parses

```bash
docker compose -f docker-compose.prod.yml config > /dev/null
```

  > Expected: exits 0. (Doesn't run anything — just validates YAML.)

### F3 + F9 — Docs render

```bash
$EDITOR docs/DEPLOYMENT.md
$EDITOR ONBOARDING.md
```

  > Expected: read like an actual runbook — no `TODO` left.

---

## When something doesn't match

- Backend changes? `docker compose restart backend` then re-check.
- Frontend changes? The dev server hot-reloads, but `app/[locale]/(app)/doctor/handoff/[id]/page.tsx` is a Client Component — sometimes a hard refresh is needed.
- Tests pass but UI is wrong? Open the page in incognito to bypass any stale auth state.
- Toast doesn't appear? Confirm you imported `<ToastViewport>` at the bottom of the page (it must be inside the React tree to render).

Once you're through this checklist you have ground truth that Phase A → F
landed as described. Save the failures (if any) and we can spawn focused fix
tasks.

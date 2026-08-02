# Audit Log Verification Runbook

> How to run and interpret the tamper-evident audit chain verification.

---

## What it checks

Every state-changing operation in MedAgent writes a row to `audit_logs` with a
hash chain:

```
sequence (BIGSERIAL) | previous_hash | current_hash | action | ...
```

The `current_hash` of row *N* is computed from:
- The row's own content (action, resource_type, resource_id, details, etc.)
- The `current_hash` of row *N-1* (the `previous_hash`)

This makes the chain **tamper-evident**: altering any row breaks every
subsequent hash.

---

## Quick check (local Docker)

```bash
make audit-verify
```

Or directly:

```bash
cd backend
uv run python ../scripts/audit_verify.py
```

Expected output when healthy:

```
OK — chain intact. Last sequence: 42
```

If tampered:

```
BROKEN at sequence 7
  expected_hash:  a3f2...
  actual_hash:    b8e1...
  row_id:         550e8400-e29b-41d4-a716-446655440000
```

---

## Admin API endpoint

Authenticated admins can verify via API:

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/admin/audit-verify
```

Response (healthy):

```json
{
  "ok": true,
  "last_sequence": 42
}
```

Response (tampered):

```json
{
  "ok": false,
  "broken_at": 7,
  "row_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## CI integration

The verification script runs automatically after the test suite in GitHub
Actions (`.github/workflows/ci.yml`). A broken chain fails the build.

---

## Manual tamper test (for developers)

1. Trigger a few actions (register, login, update profile).
2. Run `make audit-verify` → confirm `OK`.
3. Connect to the DB and manually edit one audit row:
   ```sql
   UPDATE audit_logs SET action = 'tampered' WHERE sequence = 3;
   ```
4. Re-run `make audit-verify` → confirm `BROKEN at sequence 3`.
5. **Rollback** the tamper to restore the chain:
   ```sql
   UPDATE audit_logs SET action = 'user_login' WHERE sequence = 3;
   ```

> ⚠️ Never manually edit audit rows in production. This test is for local
development only.

---

## How the hash is computed

```python
from app.common.audit_chain import compute_hash

payload = f"{previous_hash}|{action}|{resource_type}|{resource_id}|{details_json}"
current_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

The hash is computed inside a `SERIALIZABLE` transaction to prevent race
conditions between concurrent inserts.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `BROKEN at sequence 1` | Genesis row missing or DB truncated | Re-run migrations + seed |
| `BROKEN at sequence N` after restore | Forgot to rollback manual edit | Restore original row content |
| Script hangs | No `DATABASE_URL` set | Export `DATABASE_URL` or run inside Docker |
| Empty chain (no rows) | Fresh empty DB | Normal — chain is valid with 0 rows |

---

## Related files

- `backend/app/common/audit_chain.py` — hash computation + verification logic
- `backend/app/common/audit.py` — audit log insert helper
- `scripts/audit_verify.py` — standalone CLI verifier
- `backend/alembic/versions/*_audit_chain.py` — migration adding chain columns

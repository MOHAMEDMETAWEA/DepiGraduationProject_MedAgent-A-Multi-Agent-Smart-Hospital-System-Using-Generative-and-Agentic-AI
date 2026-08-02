# PHI Encryption Key Rotation Runbook

> How to safely rotate the `DATA_ENCRYPTION_KEY` used for Fernet AES-256
> application-layer encryption of sensitive patient data.

---

## When to rotate

- Every **90 days** as a routine security practice.
- Immediately after any suspicion of key compromise.
- After an employee with key access leaves the team.

---

## Prerequisites

1. **Current key** (`OLD_KEY`) — must decrypt existing data successfully.
2. **New key** (`NEW_KEY`) — generate a fresh 32-byte base64-encoded Fernet key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
3. **Maintenance window** — during rotation, encrypted fields are temporarily
   unreadable. Plan for < 5 minutes of downtime or run in a background job.
4. **Backup** — snapshot the database before starting.

---

## Rotation steps

### 1. Verify current key health

```bash
cd backend
uv run python -c "
from app.core.encryption import decrypt_phi
from app.core.config import settings
assert settings.DATA_ENCRYPTION_KEY
print('Current key valid:', len(settings.DATA_ENCRYPTION_KEY))
"
```

### 2. Enable dual-key mode

Set **both** keys in the environment temporarily:

```bash
export OLD_DATA_ENCRYPTION_KEY="<old-key>"
export DATA_ENCRYPTION_KEY="<new-key>"
```

The application reads `OLD_DATA_ENCRYPTION_KEY` as a fallback for decryption
while writing all new data with the new key.

> In `backend/app/core/encryption.py`, the ` decrypt_phi` helper should try
> `DATA_ENCRYPTION_KEY` first, then fall back to `OLD_DATA_ENCRYPTION_KEY`.

### 3. Re-encrypt existing data (background job)

Run the re-encryption script against all encrypted tables:

```bash
uv run python scripts/rotate_phi_key.py
```

This script:
1. Iterates every row in `messages`, `vision_analyses`, `patient_profiles`,
   `handoff_summaries` where `encrypted_content IS NOT NULL`.
2. Decrypts with `OLD_DATA_ENCRYPTION_KEY`.
3. Re-encrypts with `DATA_ENCRYPTION_KEY`.
4. Updates the row in a transaction.
5. Logs progress every 100 rows.

**Expected output:**

```
Re-encrypting messages ... 1500 rows done
Re-encrypting vision_analyses ... 42 rows done
Re-encrypting patient_profiles ... 89 rows done
Re-encrypting handoff_summaries ... 12 rows done
Rotation complete. 1643 rows re-encrypted.
```

### 4. Verify sample rows

```bash
uv run python -c "
import asyncio
from app.core.database import async_session
from app.models.messages import Message
from app.core.encryption import decrypt_phi

async def check():
    async with async_session() as db:
        msg = await db.get(Message, '<sample-uuid>')
        plaintext = decrypt_phi(msg.encrypted_content)
        print('Decryption OK:', plaintext[:50])

asyncio.run(check())
"
```

### 5. Remove old key

Once verification passes and the maintenance window closes:

```bash
unset OLD_DATA_ENCRYPTION_KEY
```

Update the production secret store (Railway/Render/Vercel env vars) to keep
only the new key. Remove the old key from all systems.

### 6. Post-rotation checklist

- [ ] `make test-backend` passes (especially encryption tests).
- [ ] `make audit-verify` passes (rotation is audit-logged).
- [ ] Application health checks green (`/health/ready`).
- [ ] Old key purged from env files, CI secrets, and team password managers.
- [ ] Rotation event documented in security log.

---

## Rollback plan

If re-encryption fails mid-way:

1. **Stop** the rotation script.
2. **Restore** the database snapshot taken in step 0.
3. **Revert** env vars to the old key only.
4. **Investigate** the failure before retrying.

> ⚠️ Never leave the system in a mixed-encryption state without `OLD_KEY`
> configured. That makes some rows permanently unreadable.

---

## Automation (optional)

For high-availability systems, implement the rotation as an async background
job instead of a maintenance window:

1. Add a `encryption_key_version` column to encrypted tables.
2. The background job marks rows as `re_encrypted` after processing.
3. Old key remains configured until 100% of rows are migrated.
4. A cron job or scheduler triggers the rotation job nightly until complete.

This approach is **not implemented in the MVP** but is the recommended path
for production scaling.

---

## Related files

- `backend/app/core/encryption.py` — Fernet wrapper + ORM types
- `backend/app/models/_types.py` — `EncryptedString`, `EncryptedJSON`
- `scripts/rotate_phi_key.py` — re-encryption script (create when needed)
- `docs/14_phi_encryption.md` — full encryption design doc

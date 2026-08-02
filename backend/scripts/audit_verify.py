"""Audit Chain Verification Script — التحقق من سلامة سلسلة سجل التدقيق

يمشي على كل صفوف audit_logs ويتأكد إن الـ hash chain سليمة.
لو في عبث أو تلاعب، هيرجع أول sequence مكسور.

الاستخدام:
    python scripts/audit_verify.py
"""

import asyncio

from app.common.audit_chain import GENESIS_HASH, compute_hash
from app.core.database import get_session
from app.models.audit_log import AuditLog
from sqlalchemy import select


async def verify() -> dict:
    """Run audit chain verification."""
    async with get_session() as session:
        result = await session.execute(select(AuditLog).order_by(AuditLog.sequence))
        rows = result.scalars().all()

        if not rows:
            print("No audit logs found — chain is empty (OK)")
            return {"ok": True, "last_sequence": 0, "broken_at": None}

        expected_previous = GENESIS_HASH
        for row in rows:
            computed = compute_hash(
                sequence=row.sequence,
                user_id=row.user_id,
                action=row.action,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                details=row.details,
                ip_address=str(row.ip_address) if row.ip_address else None,
                user_agent=row.user_agent,
                created_at=row.created_at,
                previous_hash=expected_previous,
            )

            if computed != row.current_hash:
                print(f"❌ BROKEN at sequence {row.sequence}!")
                print(f"   Expected: {computed}")
                print(f"   Actual:   {row.current_hash}")
                return {
                    "ok": False,
                    "last_sequence": len(rows),
                    "broken_at": row.sequence,
                }

            expected_previous = row.current_hash

        print(f"✅ Chain OK — {len(rows)} entries, last sequence: {rows[-1].sequence}")
        return {"ok": True, "last_sequence": rows[-1].sequence, "broken_at": None}


if __name__ == "__main__":
    result = asyncio.run(verify())
    exit(0 if result["ok"] else 1)

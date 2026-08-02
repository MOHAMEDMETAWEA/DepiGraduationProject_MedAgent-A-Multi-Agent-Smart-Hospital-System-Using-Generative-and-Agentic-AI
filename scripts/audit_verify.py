#!/usr/bin/env python3
"""
Audit Hash Chain Verifier — مدقق سلسلة تجزئة سجل التدقيق

يمشي على كل صفوف audit_logs ويتأكد إن سلسلة SHA-256 سليمة.
لو لقى كسر في السلسلة، بيرجع أول sequence مكسور.

الاستخدام:
    python scripts/audit_verify.py
    python scripts/audit_verify.py --verbose
    python scripts/audit_verify.py --exit-on-broken

متغيرات البيئة المطلوبة:
    DATABASE_URL — عنوان اتصال الداتابيز
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import asyncio
import argparse
from datetime import datetime, UTC

from sqlalchemy import select, text

from app.core.database import get_session
from app.models.audit_log import AuditLog
from app.common.audit_chain import GENESIS_HASH, compute_hash


async def verify_chain(verbose: bool = False) -> dict:
    """Verifies the entire audit hash chain and returns a report."""
    async with get_session() as session:
        # Count rows
        count_result = await session.execute(select(AuditLog).order_by(AuditLog.sequence))
        rows = count_result.scalars().all()

        if not rows:
            return {
                "ok": True,
                "total_rows": 0,
                "last_sequence": 0,
                "broken_at": None,
            }

        expected_previous = GENESIS_HASH
        verified = 0
        broken_at = None

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
                broken_at = row.sequence
                if verbose:
                    print(f"  ❌ Chain broken at sequence {row.sequence}:")
                    print(f"     Expected: {computed[:16]}...")
                    print(f"     Actual:   {row.current_hash[:16]}...")
                    print(f"     Action:   {row.action}")
                    print(f"     Previous: {row.previous_hash[:16]}...")
                break

            if verbose:
                print(f"  ✅ sequence={row.sequence} action={row.action} hash={computed[:12]}...")
            expected_previous = row.current_hash
            verified += 1

        return {
            "ok": broken_at is None,
            "total_rows": len(rows),
            "verified_rows": verified,
            "last_sequence": rows[-1].sequence,
            "broken_at": broken_at,
        }


def main():
    parser = argparse.ArgumentParser(description="Verify audit log hash chain integrity.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-row verification")
    parser.add_argument(
        "--exit-on-broken", action="store_true", help="Exit with code 1 if chain is broken"
    )
    args = parser.parse_args()

    print("🔍 MedAgent Audit Chain Verifier")
    print(f"   Genesis hash: {GENESIS_HASH[:16]}...")
    print()

    result = asyncio.run(verify_chain(verbose=args.verbose))

    print(f"\n📊 Results:")
    print(f"   Total rows:     {result['total_rows']}")
    print(f"   Verified rows:  {result['verified_rows']}")
    print(f"   Last sequence:  {result['last_sequence']}")
    print(f"   Chain intact:   {'✅ YES' if result['ok'] else '❌ NO'}")

    if result["broken_at"]:
        print(f"   Broken at:      sequence {result['broken_at']}")
        print(f"\n⚠️  WARNING: Audit chain tampering detected at sequence {result['broken_at']}!")
        print(f"   This means an audit row was modified, deleted, or inserted incorrectly.")
        if args.exit_on_broken:
            sys.exit(1)
    else:
        print(f"   ✅ Audit chain is intact and tamper-free.")

    if not result["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

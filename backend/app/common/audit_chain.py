"""
Audit Hash Chaining — سلسلة تجزئة سجل التدقيق (Tamper-Evident)

كل صف في audit_logs مربوط باللي قبله بـ SHA-256 hash عشان نكتشف أي عبث.
السلسلة: genesis_hash → row_1 → hash → row_2 → hash → ...

لو حد عدّل أو مسح صف، الـ hash chain هينكسر في الصف اللي بعده.

§9.7 من الخطة.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

GENESIS_LABEL = "MEDAGENT_AUDIT_GENESIS_V1"
GENESIS_HASH = hashlib.sha256(GENESIS_LABEL.encode()).hexdigest()


def compute_hash(
    *,
    sequence: int,
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str | None,
    resource_id: uuid.UUID | None,
    details: dict | None,
    ip_address: str | None,
    user_agent: str | None,
    created_at: datetime,
    previous_hash: str,
) -> str:
    """
    يحسب SHA-256 hash لصف audit.

    بنستخدم canonical JSON عشان الترتيب مضمون.
    """
    canonical = json.dumps(
        {
            "sequence": sequence,
            "user_id": str(user_id) if user_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "details": details,
            "ip_address": str(ip_address) if ip_address else None,
            "user_agent": user_agent,
            "created_at": created_at.isoformat(),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256((previous_hash + canonical).encode()).hexdigest()


def verify_chain(rows: list[dict]) -> dict:
    """
    بيمشي على سلسلة audit_logs ويتأكد من سلامتها.
    يرجع أول sequence مكسور (أو OK لو سليمة).
    """
    if not rows:
        return {"ok": True, "last_sequence": 0, "broken_at": None}

    expected_previous = GENESIS_HASH

    for row in rows:
        seq = row.get("sequence", 0)
        actual = row.get("current_hash", "")

        computed = compute_hash(
            sequence=seq,
            user_id=row.get("user_id"),
            action=row.get("action", ""),
            resource_type=row.get("resource_type"),
            resource_id=row.get("resource_id"),
            details=row.get("details"),
            ip_address=row.get("ip_address"),
            user_agent=row.get("user_agent"),
            created_at=row["created_at"],
            previous_hash=expected_previous,
        )

        if computed != actual:
            return {
                "ok": False,
                "last_sequence": row.get("sequence", 0),
                "broken_at": seq,
                "expected_hash": computed,
                "actual_hash": actual,
            }

        expected_previous = actual

    return {"ok": True, "last_sequence": rows[-1].get("sequence", 0), "broken_at": None}

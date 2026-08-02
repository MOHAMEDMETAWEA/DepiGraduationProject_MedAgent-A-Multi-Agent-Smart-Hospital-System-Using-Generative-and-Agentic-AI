from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.common.audit_chain import GENESIS_HASH, compute_hash
from app.core.database import get_session
from app.models.audit_log import AuditLog


async def _write_audit(
    action: str,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    try:
        async with get_session() as session:
            # Get last sequence + hash for the chain
            result = await session.execute(
                select(AuditLog.sequence, AuditLog.current_hash)
                .where(AuditLog.sequence.is_not(None))
                .order_by(AuditLog.sequence.desc())
                .limit(1)
            )
            last = result.first()
            next_seq = (last[0] + 1) if last else 1
            previous_hash = last[1] if last else GENESIS_HASH

            now = datetime.now(UTC)
            current_hash = compute_hash(
                sequence=next_seq,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=now,
                previous_hash=previous_hash,
            )

            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                sequence=next_seq,
                previous_hash=previous_hash,
                current_hash=current_hash,
            )
            session.add(log)
            await session.commit()
    except Exception:
        pass


def log_action(
    action: str,
    *,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Fire-and-forget audit log entry. Never blocks the main request and never raises."""
    from app.core.config import settings

    if settings.DISABLE_RATE_LIMIT:
        return  # Tests: skip fire-and-forget to avoid greenlet conflicts

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(  # noqa: RUF006 — fire-and-forget by design; never blocks the request
            _write_audit(
                action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
    except RuntimeError:
        pass  # No event loop — skip audit

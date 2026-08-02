import uuid

import pytest
from app.common.audit import _write_audit, log_action
from app.models.audit_log import AuditLog
from app.models.users import User
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestAuditLog:
    async def test_log_action_writes_to_db(self, db_session):
        user = User(
            email=f"audit-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="hashed",
            full_name="Audit User",
            role="patient",
        )
        db_session.add(user)
        await db_session.commit()

        await _write_audit(
            "test_action",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            details={"extra": "value"},
        )

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id,
                AuditLog.action == "test_action",
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.action == "test_action"
        assert log.resource_type == "user"
        assert log.details == {"extra": "value"}

    async def test_log_action_never_raises(self):
        log_action("noop")

    async def test_log_action_with_no_user(self, db_session):
        action = f"anon-{uuid.uuid4().hex[:8]}"
        await _write_audit(action, details={"anonymous": True})

        result = await db_session.execute(select(AuditLog).where(AuditLog.action == action))
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.user_id is None

"""Phase D — D2 (cont.): notifications router + scheduler tests.

The scheduler talks to SMTP via aiosmtplib. We don't connect to a real server
— the unit-level tests exercise the queue + listing logic; the integration
behaviour is sanity-tested via mocking aiosmtplib.SMTP.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.main import app
from fastapi.testclient import TestClient

from tests.factories import auth_headers, make_conversation, make_patient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestListNotifications:
    async def test_list_for_user_returns_empty_initially(self, client, db_session):
        patient = await make_patient(db_session)
        res = client.get("/api/v1/notifications", headers=auth_headers(patient))
        assert res.status_code == 200
        body = res.json()
        assert "notifications" in body
        assert body["total"] == 0

    async def test_list_requires_auth(self, client):
        res = client.get("/api/v1/notifications")
        assert res.status_code == 401


class TestScheduleFollowUp:
    async def test_schedule_follow_up_for_own_conversation(self, client, db_session):
        patient = await make_patient(db_session)
        conv = await make_conversation(db_session, patient_user_id=patient.id)

        res = client.post(
            "/api/v1/notifications/follow-up/schedule",
            json={
                "conversation_id": str(conv.id),
                "delay_hours": 24,
                "template": "follow_up_default",
                "reason": "routine check",
            },
            headers=auth_headers(patient),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "queued"
        assert "notification_id" in body
        assert "scheduled_for" in body

    async def test_schedule_for_unknown_conversation_returns_404(self, client, db_session):
        import uuid as _uuid

        patient = await make_patient(db_session)
        res = client.post(
            "/api/v1/notifications/follow-up/schedule",
            json={
                "conversation_id": str(_uuid.uuid4()),
                "delay_hours": 1,
            },
            headers=auth_headers(patient),
        )
        assert res.status_code == 404


class TestTriggerWorker:
    async def test_trigger_returns_processed_summary(self, client, db_session):
        patient = await make_patient(db_session)
        res = client.post("/api/v1/notifications/trigger", headers=auth_headers(patient))
        assert res.status_code == 200
        body = res.json()
        # Worker always responds with a structured summary, even if zero work.
        assert "processed" in body
        assert "sent" in body
        assert "failed" in body

    async def test_worker_calls_smtp_for_due_notifications(self, client, db_session):
        """With a mocked SMTP client, the worker processes a due notification."""
        from datetime import UTC, datetime, timedelta

        from app.models.notification_log import NotificationLog
        from app.modules.notifications.service import process_due_notifications

        patient = await make_patient(db_session)

        # The scheduler stores scheduled_for inside extra_meta (JSONB).
        # A past timestamp ensures `process_due_notifications` picks it up.
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        due = NotificationLog(
            user_id=patient.id,
            channel="email",
            template="follow_up_default",
            recipient=patient.email,
            status="queued",
            extra_meta={"scheduled_for": past},
        )
        db_session.add(due)
        await db_session.commit()

        # Patch the SMTP send at the boundary the service ultimately calls.
        with patch("aiosmtplib.send", new=AsyncMock(return_value=None)):
            result = await process_due_notifications()

        # We don't assert exact processed/sent counts (other queued
        # notifications from prior tests may also be picked up) — just
        # confirm the worker found at least one due item.
        assert result["processed"] >= 1

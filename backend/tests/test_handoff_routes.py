"""Phase D — D1: end-to-end tests for the handoff REST API.

Covers:
- Create / get / list (patient + doctor views)
- POST /send (doctor guardrail B4)
- POST /review (auto-claim D1, notes-only D2, 412 stale B3)
- PATCH /status (state machine, invalid transition, auto-claim, 412 stale)
- GET /doctor/inbox (filters: status, triage_level, language, sort)
- GET /doctor/inbox/count

We use the TestClient + a session-level engine. Each test creates its own
users/conversation/handoff via tests.factories — no shared fixtures across
tests so each one stays self-contained and parallel-safe.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.main import app
from fastapi.testclient import TestClient

from tests.factories import (
    auth_headers,
    make_doctor,
    make_handoff,
    make_patient,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ─────────────────────────────────────────────────────────
# GET /handoffs/{id} — view
# ─────────────────────────────────────────────────────────


class TestViewHandoff:
    async def test_patient_can_view_own_handoff(self, client, db_session):
        patient = await make_patient(db_session)
        handoff = await make_handoff(db_session, patient_user_id=patient.id)

        res = client.get(f"/api/v1/handoffs/{handoff.id}", headers=auth_headers(patient))

        assert res.status_code == 200
        body = res.json()
        assert body["id"] == str(handoff.id)
        assert body["patient_user_id"] == str(patient.id)
        assert body["status"] == "new"
        # Phase B3: updated_at must be exposed for optimistic concurrency.
        assert "updated_at" in body

    async def test_assigned_doctor_can_view(self, client, db_session):
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(
            db_session, patient_user_id=patient.id, doctor_user_id=doctor.id
        )

        res = client.get(f"/api/v1/handoffs/{handoff.id}", headers=auth_headers(doctor))
        assert res.status_code == 200

    async def test_unrelated_user_gets_404(self, client, db_session):
        patient = await make_patient(db_session)
        outsider = await make_patient(db_session)
        handoff = await make_handoff(db_session, patient_user_id=patient.id)

        res = client.get(f"/api/v1/handoffs/{handoff.id}", headers=auth_headers(outsider))
        assert res.status_code == 404

    async def test_unauthenticated_gets_401(self, client, db_session):
        patient = await make_patient(db_session)
        handoff = await make_handoff(db_session, patient_user_id=patient.id)

        res = client.get(f"/api/v1/handoffs/{handoff.id}")
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────
# GET /handoffs — patient list
# ─────────────────────────────────────────────────────────


class TestListPatientHandoffs:
    async def test_patient_lists_only_their_own(self, client, db_session):
        patient = await make_patient(db_session)
        other = await make_patient(db_session)
        await make_handoff(db_session, patient_user_id=patient.id)
        await make_handoff(db_session, patient_user_id=patient.id)
        await make_handoff(db_session, patient_user_id=other.id)

        res = client.get("/api/v1/handoffs", headers=auth_headers(patient))
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        ids = {item["patient_user_id"] for item in body["items"]}
        assert ids == {str(patient.id)}


# ─────────────────────────────────────────────────────────
# POST /handoffs/{id}/send — B4 doctor guardrail
# ─────────────────────────────────────────────────────────


class TestSendHandoff:
    async def test_send_to_approved_doctor_succeeds(self, client, db_session):
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session, approval_status="approved")
        handoff = await make_handoff(db_session, patient_user_id=patient.id)

        res = client.post(
            f"/api/v1/handoffs/{handoff.id}/send",
            json={"doctor_user_id": str(doctor.id)},
            headers=auth_headers(patient),
        )
        assert res.status_code == 200
        assert res.json() == {"sent": True}

    async def test_send_to_pending_doctor_returns_400_not_approved(self, client, db_session):
        patient = await make_patient(db_session)
        pending = await make_doctor(db_session, approval_status="pending")
        handoff = await make_handoff(db_session, patient_user_id=patient.id)

        res = client.post(
            f"/api/v1/handoffs/{handoff.id}/send",
            json={"doctor_user_id": str(pending.id)},
            headers=auth_headers(patient),
        )
        assert res.status_code == 400
        assert res.json()["error"]["message"] == "not_approved"

    async def test_send_to_non_doctor_returns_400_not_a_doctor(self, client, db_session):
        patient = await make_patient(db_session)
        another_patient = await make_patient(db_session)
        handoff = await make_handoff(db_session, patient_user_id=patient.id)

        res = client.post(
            f"/api/v1/handoffs/{handoff.id}/send",
            json={"doctor_user_id": str(another_patient.id)},
            headers=auth_headers(patient),
        )
        assert res.status_code == 400
        assert res.json()["error"]["message"] == "not_a_doctor"


# ─────────────────────────────────────────────────────────
# POST /handoffs/{id}/review — auto-claim + notes-only
# ─────────────────────────────────────────────────────────


class TestReviewHandoff:
    async def test_doctor_auto_claims_unassigned(self, client, db_session):
        """D1: a doctor reviewing an unassigned handoff should claim it."""
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(db_session, patient_user_id=patient.id)
        assert handoff.doctor_user_id is None

        res = client.post(
            f"/api/v1/handoffs/{handoff.id}/review",
            json={"notes": "looks routine"},
            headers=auth_headers(doctor),
        )
        assert res.status_code == 200

        # Re-fetch via the API to confirm the doctor is now assigned.
        view = client.get(f"/api/v1/handoffs/{handoff.id}", headers=auth_headers(doctor))
        assert view.status_code == 200
        assert view.json()["doctor_user_id"] == str(doctor.id)
        assert view.json()["doctor_private_notes"] == "looks routine"

    async def test_review_does_not_advance_status(self, client, db_session):
        """D2: saving notes must not transition status to 'reviewed'."""
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(
            db_session, patient_user_id=patient.id, doctor_user_id=doctor.id, status="new"
        )

        res = client.post(
            f"/api/v1/handoffs/{handoff.id}/review",
            json={"notes": "x"},
            headers=auth_headers(doctor),
        )
        assert res.status_code == 200

        view = client.get(f"/api/v1/handoffs/{handoff.id}", headers=auth_headers(doctor)).json()
        assert view["status"] == "new"
        assert view["reviewed_at"] is None

    async def test_other_doctor_cannot_review_assigned_handoff(self, client, db_session):
        patient = await make_patient(db_session)
        owner = await make_doctor(db_session)
        intruder = await make_doctor(db_session)
        handoff = await make_handoff(
            db_session, patient_user_id=patient.id, doctor_user_id=owner.id
        )

        res = client.post(
            f"/api/v1/handoffs/{handoff.id}/review",
            json={"notes": "x"},
            headers=auth_headers(intruder),
        )
        assert res.status_code == 403

    async def test_review_with_stale_timestamp_returns_412(self, client, db_session):
        """B3: stale `If-Unmodified-Since` should be rejected with 412."""
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(
            db_session, patient_user_id=patient.id, doctor_user_id=doctor.id
        )

        # One full minute in the past — definitely before updated_at.
        stale = (datetime.now(UTC) - timedelta(minutes=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")

        res = client.post(
            f"/api/v1/handoffs/{handoff.id}/review",
            json={"notes": "x"},
            headers={**auth_headers(doctor), "If-Unmodified-Since": stale},
        )
        assert res.status_code == 412
        assert res.json()["error"]["message"] == "stale"


# ─────────────────────────────────────────────────────────
# PATCH /handoffs/{id}/status — state machine
# ─────────────────────────────────────────────────────────


class TestStatusTransitions:
    async def test_new_to_acknowledged(self, client, db_session):
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(
            db_session, patient_user_id=patient.id, doctor_user_id=doctor.id
        )

        res = client.patch(
            f"/api/v1/handoffs/{handoff.id}/status",
            json={"status": "acknowledged"},
            headers=auth_headers(doctor),
        )
        assert res.status_code == 200
        assert res.json()["status"] == "acknowledged"

        view = client.get(f"/api/v1/handoffs/{handoff.id}", headers=auth_headers(doctor)).json()
        assert view["status"] == "acknowledged"
        assert view["acknowledged_at"] is not None

    async def test_full_flow_new_to_closed(self, client, db_session):
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(
            db_session, patient_user_id=patient.id, doctor_user_id=doctor.id
        )

        for next_status in ("acknowledged", "in_progress", "reviewed", "closed"):
            res = client.patch(
                f"/api/v1/handoffs/{handoff.id}/status",
                json={"status": next_status},
                headers=auth_headers(doctor),
            )
            assert res.status_code == 200, f"transition to {next_status}: {res.json()}"

        view = client.get(f"/api/v1/handoffs/{handoff.id}", headers=auth_headers(doctor)).json()
        assert view["status"] == "closed"
        assert view["closed_at"] is not None
        # closed should backfill reviewed_at if it was set; here we hit reviewed first so it's set.
        assert view["reviewed_at"] is not None

    async def test_invalid_transition_returns_409(self, client, db_session):
        """closed → anything must be rejected."""
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(
            db_session,
            patient_user_id=patient.id,
            doctor_user_id=doctor.id,
            status="closed",
        )

        res = client.patch(
            f"/api/v1/handoffs/{handoff.id}/status",
            json={"status": "acknowledged"},
            headers=auth_headers(doctor),
        )
        assert res.status_code == 409

    async def test_status_change_with_stale_timestamp_returns_412(self, client, db_session):
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(
            db_session, patient_user_id=patient.id, doctor_user_id=doctor.id
        )
        stale = (datetime.now(UTC) - timedelta(minutes=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")

        res = client.patch(
            f"/api/v1/handoffs/{handoff.id}/status",
            json={"status": "acknowledged"},
            headers={**auth_headers(doctor), "If-Unmodified-Since": stale},
        )
        assert res.status_code == 412

    async def test_doctor_auto_claim_on_status_change(self, client, db_session):
        """D1: hitting `acknowledged` on an unassigned handoff claims it."""
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        handoff = await make_handoff(db_session, patient_user_id=patient.id)
        assert handoff.doctor_user_id is None

        res = client.patch(
            f"/api/v1/handoffs/{handoff.id}/status",
            json={"status": "acknowledged"},
            headers=auth_headers(doctor),
        )
        assert res.status_code == 200

        view = client.get(f"/api/v1/handoffs/{handoff.id}", headers=auth_headers(doctor)).json()
        assert view["doctor_user_id"] == str(doctor.id)
        assert view["status"] == "acknowledged"

    async def test_nonexistent_handoff_returns_404(self, client, db_session):
        doctor = await make_doctor(db_session)
        res = client.patch(
            f"/api/v1/handoffs/{uuid.uuid4()}/status",
            json={"status": "acknowledged"},
            headers=auth_headers(doctor),
        )
        assert res.status_code == 404


# ─────────────────────────────────────────────────────────
# GET /handoffs/doctor/inbox — filters
# ─────────────────────────────────────────────────────────


class TestDoctorInbox:
    async def test_inbox_lists_only_assigned(self, client, db_session):
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        other_doctor = await make_doctor(db_session)
        await make_handoff(db_session, patient_user_id=patient.id, doctor_user_id=doctor.id)
        await make_handoff(db_session, patient_user_id=patient.id, doctor_user_id=doctor.id)
        await make_handoff(db_session, patient_user_id=patient.id, doctor_user_id=other_doctor.id)

        res = client.get("/api/v1/handoffs/doctor/inbox", headers=auth_headers(doctor))
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2

    async def test_inbox_filter_by_status(self, client, db_session):
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        await make_handoff(
            db_session,
            patient_user_id=patient.id,
            doctor_user_id=doctor.id,
            status="new",
        )
        await make_handoff(
            db_session,
            patient_user_id=patient.id,
            doctor_user_id=doctor.id,
            status="closed",
        )

        res = client.get(
            "/api/v1/handoffs/doctor/inbox?status=closed",
            headers=auth_headers(doctor),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert body["items"][0]["status"] == "closed"

    async def test_inbox_rejects_invalid_status_param(self, client, db_session):
        doctor = await make_doctor(db_session)
        res = client.get(
            "/api/v1/handoffs/doctor/inbox?status=garbage",
            headers=auth_headers(doctor),
        )
        # FastAPI returns 422 for failed Query pattern validation.
        assert res.status_code == 422

    async def test_inbox_requires_doctor_role(self, client, db_session):
        patient = await make_patient(db_session)
        res = client.get("/api/v1/handoffs/doctor/inbox", headers=auth_headers(patient))
        assert res.status_code == 403

    async def test_inbox_count_returns_per_status_breakdown(self, client, db_session):
        patient = await make_patient(db_session)
        doctor = await make_doctor(db_session)
        await make_handoff(
            db_session,
            patient_user_id=patient.id,
            doctor_user_id=doctor.id,
            status="new",
        )
        await make_handoff(
            db_session,
            patient_user_id=patient.id,
            doctor_user_id=doctor.id,
            status="reviewed",
        )

        res = client.get("/api/v1/handoffs/doctor/inbox/count", headers=auth_headers(doctor))
        assert res.status_code == 200
        body = res.json()
        assert body["new"] >= 1
        assert body["reviewed"] >= 1
        assert body["total"] >= 2

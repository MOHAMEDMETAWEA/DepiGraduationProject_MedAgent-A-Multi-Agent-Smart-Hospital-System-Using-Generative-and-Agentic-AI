"""Phase D — D3: SSE streaming tests for the chat endpoint.

We don't call a real LLM. The agent is patched to yield a deterministic
sequence of ``AgentEvent`` instances so we can assert:

- The endpoint streams ``text/event-stream`` with the right framing.
- Event order is preserved (start → token … → end).
- Assistant content is persisted to the DB after the stream completes.
- A safety-block event short-circuits and still terminates cleanly.
- Auth + ownership are enforced (401 / 404 before any streaming starts).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from app.ai.agent.agent import AgentEvent
from app.main import app
from app.models.messages import Message
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.factories import auth_headers, make_conversation, make_patient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _parse_sse(raw_body: bytes) -> list[dict]:
    """Parse a raw SSE response body into a list of event dicts.

    Skips empty lines and `event:` / `id:` lines we don't use.
    """
    out: list[dict] = []
    for line in raw_body.decode("utf-8").splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if not payload:
            continue
        try:
            out.append(json.loads(payload))
        except json.JSONDecodeError:
            # The chat endpoint emits raw text in some events; preserve as-is.
            out.append({"_raw": payload})
    return out


class _FakeAgent:
    """Async-iterator stand-in for the real MedAgent.

    Yields whatever ``events`` is configured with. ``run()`` takes the same
    kwargs as the real agent so the endpoint plugs in transparently.
    """

    def __init__(self, events: list[AgentEvent]):
        self._events = events

    async def run(self, **_kwargs):
        for ev in self._events:
            yield ev


def _happy_path_events() -> list[AgentEvent]:
    return [
        AgentEvent(type="start", data={"language": "en"}),
        AgentEvent(type="token", content="Hello "),
        AgentEvent(type="token", content="world."),
        AgentEvent(
            type="triage",
            data={"level": "routine", "score": 20, "flags": []},
        ),
        AgentEvent(type="end", data={}),
    ]


# ─────────────────────────────────────────────────────────
# Auth + ownership guards
# ─────────────────────────────────────────────────────────


class TestChatAuth:
    async def test_unauthenticated_chat_returns_401(self, client, db_session):
        patient = await make_patient(db_session)
        conv = await make_conversation(db_session, patient_user_id=patient.id)
        res = client.post(
            f"/api/v1/conversations/{conv.id}/chat",
            json={"message": "hi"},
        )
        assert res.status_code == 401

    async def test_chat_on_other_users_conversation_returns_404(self, client, db_session):
        patient = await make_patient(db_session)
        intruder = await make_patient(db_session)
        conv = await make_conversation(db_session, patient_user_id=patient.id)
        res = client.post(
            f"/api/v1/conversations/{conv.id}/chat",
            json={"message": "hi"},
            headers=auth_headers(intruder),
        )
        assert res.status_code == 404


# ─────────────────────────────────────────────────────────
# Stream contract
# ─────────────────────────────────────────────────────────


class TestChatStream:
    async def test_stream_emits_expected_event_order(self, client, db_session):
        patient = await make_patient(db_session)
        conv = await make_conversation(db_session, patient_user_id=patient.id)

        with patch(
            "app.modules.conversations.chat._get_agent",
            return_value=_FakeAgent(_happy_path_events()),
        ):
            res = client.post(
                f"/api/v1/conversations/{conv.id}/chat",
                json={"message": "I have a headache"},
                headers=auth_headers(patient),
            )

        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        events = _parse_sse(res.content)
        types = [ev.get("type") for ev in events if "type" in ev]
        # The endpoint may interleave citation/safety events, but the
        # primary lifecycle markers must appear in order.
        assert "start" in types
        assert "end" in types
        token_idx = [i for i, t in enumerate(types) if t == "token"]
        assert token_idx, "expected at least one token event"
        assert types.index("start") < min(token_idx) < types.index("end")

    async def test_stream_persists_assistant_message(self, client, db_session):
        """After streaming, the concatenated tokens should be saved to DB."""
        patient = await make_patient(db_session)
        conv = await make_conversation(db_session, patient_user_id=patient.id)

        with patch(
            "app.modules.conversations.chat._get_agent",
            return_value=_FakeAgent(_happy_path_events()),
        ):
            res = client.post(
                f"/api/v1/conversations/{conv.id}/chat",
                json={"message": "hi"},
                headers=auth_headers(patient),
            )
        assert res.status_code == 200
        # Consume the body so the StreamingResponse finalizer runs (it
        # writes the assistant message at the end of the stream).
        _ = res.content

        msgs = (
            (
                await db_session.execute(
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(Message.created_at)
                )
            )
            .scalars()
            .all()
        )
        # Expect at least: user message + 1 assistant message.
        roles = [m.role for m in msgs]
        assert "user" in roles
        assert "assistant" in roles
        # The assistant text should equal the concatenation of token contents.
        asst = next(m for m in msgs if m.role == "assistant")
        assert asst.text == "Hello world."

    async def test_safety_block_event_is_emitted_and_terminates(self, client, db_session):
        """If the agent emits a 'safety' event, it must reach the client and
        the stream must still complete cleanly (no hang, no 5xx)."""
        patient = await make_patient(db_session)
        conv = await make_conversation(db_session, patient_user_id=patient.id)

        blocked = [
            AgentEvent(type="start", data={"language": "en"}),
            AgentEvent(
                type="safety",
                data={"blocked": True, "reason": "hallucination", "score": 0.95},
            ),
            AgentEvent(type="end", data={}),
        ]
        with patch(
            "app.modules.conversations.chat._get_agent",
            return_value=_FakeAgent(blocked),
        ):
            res = client.post(
                f"/api/v1/conversations/{conv.id}/chat",
                json={"message": "x"},
                headers=auth_headers(patient),
            )
        assert res.status_code == 200
        events = _parse_sse(res.content)
        types = [ev.get("type") for ev in events if "type" in ev]
        assert "safety" in types
        assert types.count("safety") >= 1
        assert types[-1] == "end"

    async def test_empty_agent_stream_still_returns_valid_response(self, client, db_session):
        """If the agent yields nothing, the endpoint should still produce a
        well-formed empty SSE response and not crash the downstream save path."""
        patient = await make_patient(db_session)
        conv = await make_conversation(db_session, patient_user_id=patient.id)

        with patch(
            "app.modules.conversations.chat._get_agent",
            return_value=_FakeAgent([]),
        ):
            res = client.post(
                f"/api/v1/conversations/{conv.id}/chat",
                json={"message": "noop"},
                headers=auth_headers(patient),
            )
        assert res.status_code == 200
        # Body is empty → no `data:` lines.
        assert b"data:" not in res.content

    async def test_triage_event_updates_conversation(self, client, db_session):
        """The endpoint should persist triage_level + score when the agent
        emits a triage event."""
        from app.models.conversation import Conversation

        patient = await make_patient(db_session)
        conv = await make_conversation(db_session, patient_user_id=patient.id, triage_level=None)

        with patch(
            "app.modules.conversations.chat._get_agent",
            return_value=_FakeAgent(_happy_path_events()),
        ):
            res = client.post(
                f"/api/v1/conversations/{conv.id}/chat",
                json={"message": "x"},
                headers=auth_headers(patient),
            )
        assert res.status_code == 200
        _ = res.content

        refreshed = await db_session.get(Conversation, conv.id)
        await db_session.refresh(refreshed)
        # Triage came through as level='routine', score=20.
        assert refreshed.triage_level == "routine"
        assert refreshed.triage_score == 20

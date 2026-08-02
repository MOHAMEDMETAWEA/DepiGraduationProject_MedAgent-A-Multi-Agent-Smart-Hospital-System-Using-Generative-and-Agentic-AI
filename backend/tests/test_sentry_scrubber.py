"""Tests for the Sentry PHI scrubber (Phase C — C4).

We don't initialise Sentry in tests — we exercise the pure scrub function
that runs inside the SDK's before_send hook.
"""

from __future__ import annotations

from app.core.sentry import _REDACTED, _before_send, scrub_phi


class TestScrubPhi:
    def test_redacts_top_level_phi_keys(self):
        payload = {
            "patient_name": "Sara",
            "email": "x@y.z",
            "phone": "+201234567890",
            "innocent": "keep me",
        }
        out = scrub_phi(payload)
        assert out["patient_name"] == _REDACTED
        assert out["email"] == _REDACTED
        assert out["phone"] == _REDACTED
        assert out["innocent"] == "keep me"

    def test_redacts_nested_dicts(self):
        payload = {"user": {"full_name": "Ahmed", "id": "abc"}}
        out = scrub_phi(payload)
        assert out["user"]["full_name"] == _REDACTED
        assert out["user"]["id"] == "abc"

    def test_walks_lists(self):
        # Use a list under a non-PHI key so scrub recurses into items.
        # (A key like "messages" would itself match the PHI regex and the
        # entire list would be redacted — which is the desired behaviour
        # for PHI-named container keys.)
        payload = {
            "history": [
                {"text": "I have headache", "role": "user"},
                {"text": "Consider X", "role": "assistant"},
            ],
        }
        out = scrub_phi(payload)
        assert out["history"][0]["text"] == _REDACTED
        assert out["history"][1]["text"] == _REDACTED
        assert out["history"][0]["role"] == "user"

    def test_phi_keyed_list_is_redacted_wholesale(self):
        # A list under a PHI-named key is replaced as a whole — we do NOT
        # walk into it (the key name itself is the signal).
        payload = {"messages": [{"text": "x"}, {"text": "y"}]}
        out = scrub_phi(payload)
        assert out["messages"] == _REDACTED

    def test_handles_non_dict_inputs(self):
        assert scrub_phi("plain string") == "plain string"
        assert scrub_phi(42) == 42
        assert scrub_phi(None) is None

    def test_case_insensitive_match(self):
        payload = {"PATIENT_NAME": "Ali", "Email": "a@b.c"}
        out = scrub_phi(payload)
        assert out["PATIENT_NAME"] == _REDACTED
        assert out["Email"] == _REDACTED


class TestBeforeSendHook:
    def test_redacts_request_payload(self):
        event = {
            "request": {
                "data": {"notes": "secret", "id": "123"},
                "headers": {"Authorization": "Bearer xxx", "User-Agent": "test"},
            }
        }
        out = _before_send(event, {})
        assert out is not None
        assert out["request"]["data"]["notes"] == _REDACTED
        assert out["request"]["data"]["id"] == "123"

    def test_redacts_extra_and_contexts(self):
        event = {
            "extra": {"summary": "long medical text", "case_id": "uuid"},
            "contexts": {"patient": {"name": "X"}},
        }
        out = _before_send(event, {})
        assert out["extra"]["summary"] == _REDACTED
        assert out["extra"]["case_id"] == "uuid"
        assert out["contexts"]["patient"]["name"] == _REDACTED

    def test_redacts_breadcrumbs(self):
        event = {
            "breadcrumbs": {
                "values": [
                    {"category": "http", "data": {"message": "headache 3 days"}},
                ]
            }
        }
        out = _before_send(event, {})
        assert out["breadcrumbs"]["values"][0]["data"]["message"] == _REDACTED

    def test_returns_event_even_when_payload_is_unusual(self):
        # Should not raise on partial events.
        out = _before_send({}, {})
        assert out == {}

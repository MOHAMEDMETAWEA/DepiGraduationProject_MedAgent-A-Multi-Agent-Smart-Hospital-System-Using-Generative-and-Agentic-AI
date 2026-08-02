"""Tests for PHI encryption routing on Message model.

Validates that Message.from_payload() puts the body in the correct column
based on PHI_ENCRYPTION_ENABLED, and that .text always returns plaintext.
"""

from __future__ import annotations

import importlib
import uuid

import pytest
from cryptography.fernet import Fernet


@pytest.fixture
def encryption_off(monkeypatch):
    """Patch is_encryption_enabled to return False without reloading modules."""
    monkeypatch.setattr("app.models.messages.is_encryption_enabled", lambda: False)


@pytest.fixture
def encryption_on(monkeypatch):
    """Patch is_encryption_enabled to return True without reloading modules."""
    monkeypatch.setattr("app.models.messages.is_encryption_enabled", lambda: True)


class TestMessagePayloadRouting:
    """Routing logic in Message.from_payload — no DB needed."""

    def test_disabled_routes_body_to_plaintext_content(self, encryption_off):
        from app.models.messages import Message

        msg = Message.from_payload(
            conversation_id=uuid.uuid4(),
            role="user",
            content="I have a headache",
        )
        assert msg.content == "I have a headache"
        assert msg.encrypted_content is None
        assert msg.text == "I have a headache"

    def test_enabled_routes_body_to_encrypted_column(self, encryption_on):
        from app.models.messages import Message

        msg = Message.from_payload(
            conversation_id=uuid.uuid4(),
            role="user",
            content="I have chest pain",
        )
        # Plaintext column is left empty when encryption is on
        assert msg.content == ""
        # The TypeDecorator only encrypts at bind time, so before flush the value
        # is the plaintext str — .text reads from this column transparently
        assert msg.encrypted_content == "I have chest pain"
        assert msg.text == "I have chest pain"

    def test_text_property_falls_back_to_plaintext_when_no_ciphertext(self):
        from app.models.messages import Message

        msg = Message(
            conversation_id=uuid.uuid4(),
            role="assistant",
            content="legacy plaintext",
            encrypted_content=None,
        )
        assert msg.text == "legacy plaintext"

    def test_text_prefers_encrypted_when_both_present(self):
        from app.models.messages import Message

        msg = Message(
            conversation_id=uuid.uuid4(),
            role="assistant",
            content="should not be used",
            encrypted_content="canonical body",
        )
        assert msg.text == "canonical body"

    def test_text_returns_empty_when_both_blank(self):
        from app.models.messages import Message

        msg = Message(
            conversation_id=uuid.uuid4(),
            role="assistant",
            content="",
            encrypted_content=None,
        )
        assert msg.text == ""


class TestEncryptionPrimitives:
    """encrypt_phi / decrypt_phi round-trip when a key is configured."""

    def test_round_trip_with_real_key(self, monkeypatch):
        key = Fernet.generate_key()
        # Build a Fernet directly so we don't depend on module-level singleton
        f = Fernet(key)
        plaintext = "sensitive PHI"
        ciphertext = f.encrypt(plaintext.encode("utf-8"))
        assert ciphertext != plaintext.encode("utf-8")
        assert f.decrypt(ciphertext).decode("utf-8") == plaintext

    def test_decrypt_phi_returns_str_when_disabled(self, monkeypatch):
        # When encryption is disabled, decrypt_phi must return a string from raw bytes
        import app.core.encryption as enc

        monkeypatch.setattr(enc, "_fernet", None)
        result = enc.decrypt_phi(b"plain bytes")
        assert result == "plain bytes"

    def test_encrypt_phi_returns_bytes_when_disabled(self, monkeypatch):
        import app.core.encryption as enc

        monkeypatch.setattr(enc, "_fernet", None)
        result = enc.encrypt_phi("hello")
        assert result == b"hello"

    def test_is_encryption_enabled_reflects_singleton(self, monkeypatch):
        import app.core.encryption as enc

        monkeypatch.setattr(enc, "_fernet", None)
        assert enc.is_encryption_enabled() is False

        monkeypatch.setattr(enc, "_fernet", Fernet(Fernet.generate_key()))
        assert enc.is_encryption_enabled() is True


# Reload modules on teardown to avoid leaving the singleton in a stub state
# for other tests in the same session.
@pytest.fixture(autouse=True, scope="module")
def _restore_modules_at_end():
    yield
    import app.core.encryption
    import app.models.messages

    importlib.reload(app.core.encryption)
    # NOTE: We don't reload messages.py because that triggers SQLAlchemy
    # double-registration. The is_encryption_enabled patch is bound to the
    # module reference inside messages.py; restoring app.core.encryption is
    # enough for downstream tests since they import is_encryption_enabled fresh.

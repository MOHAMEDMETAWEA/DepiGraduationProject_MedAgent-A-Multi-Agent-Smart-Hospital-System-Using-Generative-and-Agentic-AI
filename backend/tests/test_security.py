from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from jose import JWTError


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "StrongP@ssw0rd!"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct")

        assert verify_password("wrong", hashed) is False

    def test_hash_is_deterministic(self):
        """Each hash should be different (unique salt)."""
        h1 = hash_password("same")
        h2 = hash_password("same")

        assert h1 != h2


class TestJWT:
    def test_create_and_decode_access_token(self):
        token = create_access_token(user_id="user-1", role="patient")
        payload = decode_access_token(token)

        assert payload["sub"] == "user-1"
        assert payload["role"] == "patient"
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_expired_token(self):
        with patch("app.core.security.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, tzinfo=UTC)
            expired = create_access_token("user-1", "patient")

        with pytest.raises(JWTError):
            decode_access_token(expired)

    def test_invalid_token(self):
        with pytest.raises(JWTError):
            decode_access_token("not.a.valid.token")

    def test_tampered_token(self):
        token = create_access_token("user-1", "patient")
        # Change the last character of the signature (3rd segment)
        parts = token.rsplit(".", 1)
        tampered = f"{parts[0]}.{parts[1][::-1]}"  # reverse signature

        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_extra_claims(self):
        token = create_access_token("user-1", "patient", extra_claims={"locale": "ar"})
        payload = decode_access_token(token)

        assert payload["locale"] == "ar"


class TestRefreshToken:
    def test_generate_is_random(self):
        t1 = generate_refresh_token()
        t2 = generate_refresh_token()

        assert t1 != t2
        assert len(t1) > 32  # 256-bit in base64 is ~43 chars

    def test_hash_token(self):
        raw = "test-token-value"
        hashed = hash_token(raw)

        assert hashed != raw
        assert len(hashed) == 64  # SHA-256 hex is 64 chars
        # same input = same hash
        assert hash_token(raw) == hashed

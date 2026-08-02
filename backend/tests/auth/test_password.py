import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.security import hash_password, hash_token
from app.main import app
from app.models.auth_token import AuthToken
from app.models.users import User
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def unique_email():
    return f"pw-{uuid.uuid4().hex[:8]}@test.com"


async def _create_user(db_session, email: str, password: str):
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name="Test User",
        role="patient",
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()


def _login(client, email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 200
    return response.json()


class TestChangePassword:
    async def test_change_password_valid(self, client, unique_email, db_session):
        await _create_user(db_session, unique_email, "OldPass123!")
        tokens = _login(client, unique_email, "OldPass123!")
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "OldPass123!",
                "new_password": "NewPass456!",
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200
        assert response.json() == {"changed": True}
        old_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "OldPass123!",
            },
        )
        assert old_login.status_code == 401
        new_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "NewPass456!",
            },
        )
        assert new_login.status_code == 200

    async def test_change_password_wrong_current(self, client, unique_email, db_session):
        await _create_user(db_session, unique_email, "TestPass123!")
        tokens = _login(client, unique_email, "TestPass123!")
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongCurrentPass",
                "new_password": "NewPass456!",
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 400


class TestForgotPassword:
    async def test_forgot_password_always_returns_ok(self, client):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "nonexistent@test.com",
            },
        )
        assert response.status_code == 200
        assert response.json() == {"sent": True}

    async def test_forgot_password_existing_user(self, client, unique_email, db_session):
        await _create_user(db_session, unique_email, "TestPass123!")
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": unique_email,
            },
        )
        assert response.status_code == 200
        assert response.json() == {"sent": True}


class TestResetPassword:
    async def test_reset_password_valid(self, client, unique_email, db_session):
        user = User(
            email=unique_email,
            hashed_password=hash_password("OldPass123!"),
            full_name="Reset User",
            role="patient",
            is_email_verified=True,
        )
        db_session.add(user)
        await db_session.flush()
        raw_token = uuid.uuid4().hex
        auth_token = AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="password_reset",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db_session.add(auth_token)
        await db_session.commit()

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewPass456!",
            },
        )
        assert response.status_code == 200
        assert response.json() == {"reset": True}
        old_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "OldPass123!",
            },
        )
        assert old_login.status_code == 401
        new_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "NewPass456!",
            },
        )
        assert new_login.status_code == 200

    async def test_reset_password_invalid_token(self, client):
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token-xyz",
                "new_password": "NewPass456!",
            },
        )
        assert response.status_code == 400

    async def test_reset_password_expired_token(self, client, unique_email, db_session):
        user = User(
            email=unique_email,
            hashed_password=hash_password("OldPass123!"),
            full_name="Expired Reset",
            role="patient",
            is_email_verified=True,
        )
        db_session.add(user)
        await db_session.flush()
        raw_token = uuid.uuid4().hex
        auth_token = AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="password_reset",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(auth_token)
        await db_session.commit()

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewPass456!",
            },
        )
        assert response.status_code == 400

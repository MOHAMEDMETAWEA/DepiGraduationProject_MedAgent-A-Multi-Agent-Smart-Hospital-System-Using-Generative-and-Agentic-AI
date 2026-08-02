import uuid

import pytest
from app.core.security import hash_password
from app.main import app
from app.models.users import User
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def unique_email():
    return f"token-{uuid.uuid4().hex[:8]}@test.com"


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


class TestRefresh:
    async def test_refresh_valid(self, client, unique_email, db_session):
        await _create_user(db_session, unique_email, "TestPass123!")
        tokens = _login(client, unique_email, "TestPass123!")
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        old_resp = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert old_resp.status_code == 401

    async def test_refresh_invalid_token(self, client):
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid-token-that-does-not-exist",
            },
        )
        assert response.status_code == 401

    async def test_refresh_replayed_token(self, client, unique_email, db_session):
        await _create_user(db_session, unique_email, "TestPass123!")
        tokens = _login(client, unique_email, "TestPass123!")
        r1 = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert r1.status_code == 200
        new_tokens = r1.json()
        r2 = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert r2.status_code == 401
        r3 = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": new_tokens["refresh_token"],
            },
        )
        assert r3.status_code == 401


class TestLogout:
    async def test_logout_revokes_token(self, client, unique_email, db_session):
        await _create_user(db_session, unique_email, "TestPass123!")
        tokens = _login(client, unique_email, "TestPass123!")
        logout_resp = client.post(
            "/api/v1/auth/logout",
            json={
                "refresh_token": tokens["refresh_token"],
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert logout_resp.status_code == 204
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert refresh_resp.status_code == 401

    async def test_logout_missing_auth(self, client):
        response = client.post(
            "/api/v1/auth/logout",
            json={
                "refresh_token": "some-token",
            },
        )
        assert response.status_code == 401

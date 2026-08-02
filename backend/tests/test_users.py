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
    return f"user-{uuid.uuid4().hex[:8]}@test.com"


async def _create_and_login(client, db_session, email: str, role: str = "patient"):
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Profile User",
        role=role,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPass123!",
        },
    )
    assert resp.status_code == 200, resp.json()
    return resp.json()["access_token"]


class TestGetMe:
    async def test_get_me_authenticated(self, client, unique_email, db_session):
        token = await _create_and_login(client, db_session, unique_email)
        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == unique_email
        assert data["user"]["role"] == "patient"

    async def test_get_me_unauthorized(self, client):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client):
        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": "Bearer invalid-token",
            },
        )
        assert response.status_code == 401


class TestUpdateMe:
    async def test_update_full_name(self, client, unique_email, db_session):
        token = await _create_and_login(client, db_session, unique_email)
        response = client.put(
            "/api/v1/users/me",
            json={
                "full_name": "Updated Name",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["user"]["full_name"] == "Updated Name"

    async def test_update_locale(self, client, unique_email, db_session):
        token = await _create_and_login(client, db_session, unique_email)
        response = client.put(
            "/api/v1/users/me",
            json={
                "locale": "en",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["user"]["locale"] == "en"


class TestUpdateProfile:
    async def test_update_patient_profile(self, client, unique_email, db_session):
        token = await _create_and_login(client, db_session, unique_email)
        response = client.patch(
            "/api/v1/users/me/profile",
            json={
                "gender": "male",
                "blood_type": "O+",
                "allergies": ["penicillin"],
                "chronic_conditions": ["asthma"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        profile = response.json()["profile"]
        assert profile["gender"] == "male"
        assert profile["blood_type"] == "O+"
        assert "penicillin" in profile["allergies"]


class TestDeleteMe:
    async def test_delete_account(self, client, unique_email, db_session):
        token = await _create_and_login(client, db_session, unique_email)
        response = client.delete(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status_code == 204
        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status_code == 404

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.security import hash_token
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
    return f"reg-{uuid.uuid4().hex[:8]}@test.com"


class TestRegister:
    async def test_register_patient(self, client, unique_email):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "TestPass123!",
                "full_name": "Test Patient",
                "role": "patient",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == unique_email
        assert data["role"] == "patient"
        assert data["requires_email_verification"] is True

    async def test_register_doctor(self, client, unique_email):
        license_num = f"EG-{uuid.uuid4().hex[:6].upper()}"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "TestPass123!",
                "full_name": "Dr. Test",
                "role": "doctor",
                "license_number": license_num,
                "specialty": "Cardiology",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "doctor"

    async def test_duplicate_email(self, client, unique_email):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "TestPass123!",
                "full_name": "Dup User",
            },
        )
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "TestPass123!",
                "full_name": "Dup User",
            },
        )
        assert response.status_code == 400

    async def test_weak_password(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@test.com",
                "password": "123",
                "full_name": "Weak",
            },
        )
        assert response.status_code == 422

    async def test_doctor_missing_license(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "bad-doctor@test.com",
                "password": "TestPass123!",
                "full_name": "Bad Doctor",
                "role": "doctor",
            },
        )
        assert response.status_code == 422


class TestVerifyEmail:
    async def test_verify_invalid_token(self, client):
        response = client.post(
            "/api/v1/auth/verify-email",
            json={
                "token": "invalid-token-that-does-not-exist",
            },
        )
        assert response.status_code == 400

    async def test_verify_expired_token(self, client, db_session):
        user = User(
            email=f"expired-verify-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="hashed",
            full_name="Expired User",
            role="patient",
            is_email_verified=False,
        )
        db_session.add(user)
        await db_session.flush()
        raw_token = uuid.uuid4().hex
        auth_token = AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="email_verify",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(auth_token)
        await db_session.commit()

        response = client.post(
            "/api/v1/auth/verify-email",
            json={
                "token": raw_token,
            },
        )
        assert response.status_code == 400

    async def test_verify_already_used_token(self, client, db_session):
        user = User(
            email=f"used-verify-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="hashed",
            full_name="Used User",
            role="patient",
            is_email_verified=False,
        )
        db_session.add(user)
        await db_session.flush()
        raw_token = uuid.uuid4().hex
        auth_token = AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="email_verify",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            used_at=datetime.now(UTC),
        )
        db_session.add(auth_token)
        await db_session.commit()

        response = client.post(
            "/api/v1/auth/verify-email",
            json={
                "token": raw_token,
            },
        )
        assert response.status_code == 400

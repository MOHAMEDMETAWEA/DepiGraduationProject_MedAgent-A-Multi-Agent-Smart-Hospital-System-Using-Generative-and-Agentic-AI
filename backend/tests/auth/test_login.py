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
    return f"login-{uuid.uuid4().hex[:8]}@test.com"


class TestLogin:
    async def test_login_valid_patient(self, client, unique_email, db_session):
        user = User(
            email=unique_email,
            hashed_password=hash_password("TestPass123!"),
            full_name="Test User",
            role="patient",
            is_email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == unique_email

    async def test_login_wrong_password(self, client, unique_email, db_session):
        user = User(
            email=unique_email,
            hashed_password=hash_password("TestPass123!"),
            full_name="Test User",
            role="patient",
            is_email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "WrongPassword",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_email(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "no-such-user@test.com",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 401

    async def test_login_doctor_pending(self, client, unique_email, db_session):
        user = User(
            email=unique_email,
            hashed_password=hash_password("TestPass123!"),
            full_name="Dr. Test",
            role="doctor",
            is_email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        # Create a pending doctor profile via DB directly
        from app.models.doctor_profile import DoctorProfile

        profile = DoctorProfile(
            user_id=user.id,
            license_number=f"EG-{uuid.uuid4().hex[:6].upper()}",
            specialty="Surgery",
            approval_status="pending",
        )
        db_session.add(profile)
        await db_session.commit()
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 401

    async def test_login_weak_password_validation(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@test.com",
                "password": "123",
                "full_name": "Weak",
            },
        )
        assert response.status_code == 422

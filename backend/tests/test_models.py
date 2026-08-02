from datetime import date

import pytest
from app.models.conversation import Conversation
from app.models.patient_profile import PatientProfile
from app.models.users import User
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestUserModel:
    async def test_create_user(self, db_session):
        user = User(
            email="test@example.com",
            hashed_password="hashed-test",
            full_name="Test User",
            role="patient",
        )
        db_session.add(user)
        await db_session.flush()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_email_verified is False
        assert user.locale == "ar"

    async def test_update_user(self, db_session):
        user = User(
            email="update@example.com",
            hashed_password="hashed",
            full_name="Update Me",
            role="patient",
        )
        db_session.add(user)
        await db_session.flush()

        user.full_name = "Updated Name"
        await db_session.flush()

        result = await db_session.execute(select(User).where(User.email == "update@example.com"))
        fetched = result.scalar_one()
        assert fetched.full_name == "Updated Name"

    async def test_role_constraint(self, db_session):
        user = User(
            email="role@example.com",
            hashed_password="hashed",
            full_name="Role Test",
            role="admin",
        )
        db_session.add(user)
        await db_session.flush()
        assert user.role == "admin"


class TestPatientProfile:
    async def test_create_profile(self, db_session):
        user = User(
            email="profile@example.com",
            hashed_password="hashed",
            full_name="Profile User",
            role="patient",
        )
        db_session.add(user)
        await db_session.flush()

        profile = PatientProfile(
            user_id=user.id,
            date_of_birth=date(1990, 1, 1),
            gender="male",
            allergies=["aspirin"],
            chronic_conditions=["diabetes"],
        )
        db_session.add(profile)
        await db_session.flush()

        assert profile.user_id == user.id
        assert "aspirin" in profile.allergies


class TestConversation:
    async def test_create_conversation(self, db_session):
        user = User(
            email="conv@example.com",
            hashed_password="hashed",
            full_name="Conv User",
            role="patient",
        )
        db_session.add(user)
        await db_session.flush()

        conv = Conversation(
            patient_user_id=user.id,
            title="Test Chat",
        )
        db_session.add(conv)
        await db_session.flush()

        assert conv.status == "active"
        assert conv.language == "ar"

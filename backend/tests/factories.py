"""Manual test factories — keep test setup short and the intent obvious.

Why not polyfactory? Adding another dep + dataclass introspection adds more
than the savings here. These helpers fit on one screen, defaults match the
real defaults from the SQLAlchemy models, and every factory returns a
*detached* instance the test commits at the right point.

Usage:

    async def test_my_thing(db_session):
        patient = await make_patient(db_session)
        handoff = await make_handoff(db_session, patient_user_id=patient.id)
        ...
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.security import create_access_token, hash_password
from app.models.conversation import Conversation
from app.models.doctor_profile import DoctorProfile
from app.models.handoff_summary import HandoffSummary
from app.models.messages import Message
from app.models.users import User
from sqlalchemy.ext.asyncio import AsyncSession

# ── Token helper ──────────────────────────────────────────


def make_access_token(user: User) -> str:
    """Mint a valid JWT access token for an authenticated request."""
    return create_access_token(str(user.id), user.role)


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(user)}"}


# ── User factories ────────────────────────────────────────


async def make_user(
    session: AsyncSession,
    *,
    role: str = "patient",
    email: str | None = None,
    full_name: str | None = None,
    password: str = "TestPass123!",
    is_email_verified: bool = True,
    locale: str = "en",
) -> User:
    """Create + commit a User with sensible defaults."""
    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=email or f"{role}-{suffix}@test.com",
        hashed_password=hash_password(password),
        full_name=full_name or f"{role.title()} {suffix}",
        role=role,
        is_email_verified=is_email_verified,
        locale=locale,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def make_patient(session: AsyncSession, **kw) -> User:
    return await make_user(session, role="patient", **kw)


async def make_doctor(
    session: AsyncSession,
    *,
    approval_status: str = "approved",
    specialty: str = "General Practice",
    license_number: str | None = None,
    **kw,
) -> User:
    """Create an approved doctor by default. Override ``approval_status='pending'``
    to exercise the doctor guardrail (B4)."""
    user = await make_user(session, role="doctor", **kw)
    profile = DoctorProfile(
        user_id=user.id,
        license_number=license_number or f"LIC-{uuid.uuid4().hex[:10]}",
        specialty=specialty,
        bio="Test doctor",
        years_of_experience=5,
        languages=["en", "ar"],
        approval_status=approval_status,
    )
    session.add(profile)
    await session.commit()
    return user


async def make_admin(session: AsyncSession, **kw) -> User:
    return await make_user(session, role="admin", **kw)


# ── Conversation + message factories ──────────────────────


async def make_conversation(
    session: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    language: str = "en",
    triage_level: str | None = "urgent",
    triage_score: int | None = 60,
    status: str = "active",
    red_flags_detected: list[dict] | None = None,
) -> Conversation:
    conv = Conversation(
        patient_user_id=patient_user_id,
        language=language,
        triage_level=triage_level,
        triage_score=triage_score,
        status=status,
        red_flags_detected=red_flags_detected or [],
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def make_message(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    role: str = "user",
    text: str = "I have a headache for 3 days.",
) -> Message:
    """Create + commit a Message. Uses the model's encryption-aware factory."""
    msg = Message.from_payload(conversation_id=conversation_id, role=role, content=text)
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


# ── Handoff factory ───────────────────────────────────────


async def make_handoff(
    session: AsyncSession,
    *,
    patient_user_id: uuid.UUID,
    conversation_id: uuid.UUID | None = None,
    doctor_user_id: uuid.UUID | None = None,
    status: str = "new",
    priority: int = 0,
    summary_markdown: str = "## Test handoff\nPatient reports headache.",
    sent_at: datetime | None = None,
    target_language: str = "en",
) -> HandoffSummary:
    """Create a handoff. If ``conversation_id`` is None, a fresh conversation
    is created for the same patient."""
    if conversation_id is None:
        conv = await make_conversation(session, patient_user_id=patient_user_id)
        conversation_id = conv.id

    if doctor_user_id is not None and sent_at is None:
        sent_at = datetime.now(UTC)

    handoff = HandoffSummary(
        conversation_id=conversation_id,
        patient_user_id=patient_user_id,
        doctor_user_id=doctor_user_id,
        status=status,
        priority=priority,
        summary_markdown=summary_markdown,
        sent_at=sent_at,
        target_language=target_language,
    )
    session.add(handoff)
    await session.commit()
    await session.refresh(handoff)
    return handoff

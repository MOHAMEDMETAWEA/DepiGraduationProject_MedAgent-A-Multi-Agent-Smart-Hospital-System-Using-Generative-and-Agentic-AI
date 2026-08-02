import uuid

from sqlalchemy import select

from app.common.audit import log_action
from app.core.database import get_session
from app.models.doctor_profile import DoctorProfile
from app.models.patient_profile import PatientProfile
from app.models.users import User


async def get_me(user_id: uuid.UUID) -> dict:
    from fastapi import HTTPException, status

    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user_data = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "is_email_verified": user.is_email_verified,
            "locale": user.locale,
            "avatar_url": user.avatar_url,
            "last_login_at": (user.last_login_at.isoformat() if user.last_login_at else None),
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

        profile = None
        if user.role == "patient":
            result = await session.execute(
                select(PatientProfile).where(PatientProfile.user_id == user.id)
            )
            pp = result.scalar_one_or_none()
            if pp:
                profile = {
                    "date_of_birth": (pp.date_of_birth.isoformat() if pp.date_of_birth else None),
                    "gender": pp.gender,
                    "blood_type": pp.blood_type,
                    "allergies": pp.allergies,
                    "chronic_conditions": pp.chronic_conditions,
                    "current_medications": pp.current_medications,
                    "emergency_contact_name": pp.emergency_contact_name,
                    "emergency_contact_phone": pp.emergency_contact_phone,
                }
        elif user.role == "doctor":
            result = await session.execute(
                select(DoctorProfile).where(DoctorProfile.user_id == user.id)
            )
            dp = result.scalar_one_or_none()
            if dp:
                profile = {
                    "license_number": dp.license_number,
                    "specialty": dp.specialty,
                    "bio": dp.bio,
                    "years_of_experience": dp.years_of_experience,
                    "languages": dp.languages,
                    "approval_status": dp.approval_status,
                }

        return {"user": user_data, "profile": profile}


async def update_me(user_id: uuid.UUID, data: dict) -> dict:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at:
            raise ValueError("User not found")

        for field in ("full_name", "phone", "locale"):
            if field in data and data[field] is not None:
                setattr(user, field, data[field])

        await session.commit()
        log_action("profile_update", user_id=user_id, resource_type="user", resource_id=user_id)
        return await get_me(user_id)


async def update_profile(user_id: uuid.UUID, role: str, data: dict) -> dict:
    async with get_session() as session:
        if role == "patient":
            profile = (
                await session.execute(
                    select(PatientProfile).where(PatientProfile.user_id == user_id)
                )
            ).scalar_one_or_none()
            if not profile:
                profile = PatientProfile(user_id=user_id)
                session.add(profile)
                await session.flush()
            for field in (
                "date_of_birth",
                "gender",
                "blood_type",
                "allergies",
                "chronic_conditions",
                "current_medications",
                "emergency_contact_name",
                "emergency_contact_phone",
            ):
                if field in data and data[field] is not None:
                    setattr(profile, field, data[field])
        elif role == "doctor":
            profile = (
                await session.execute(select(DoctorProfile).where(DoctorProfile.user_id == user_id))
            ).scalar_one_or_none()
            if not profile:
                raise ValueError("Doctor profile not found")
            for field in ("specialty", "bio", "years_of_experience", "languages"):
                if field in data and data[field] is not None:
                    setattr(profile, field, data[field])

        await session.commit()
        return await get_me(user_id)


async def delete_me(user_id: uuid.UUID) -> None:
    from datetime import UTC, datetime

    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        user.deleted_at = datetime.now(UTC)
        await session.commit()
        log_action("account_delete", user_id=user_id, resource_type="user", resource_id=user_id)

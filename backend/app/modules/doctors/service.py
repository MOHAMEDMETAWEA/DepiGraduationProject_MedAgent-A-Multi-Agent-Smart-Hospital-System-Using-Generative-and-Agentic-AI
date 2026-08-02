"""Doctor service — business logic for doctor profiles."""

import uuid

from sqlalchemy import func, select

from app.core.database import get_session
from app.models.doctor_profile import DoctorProfile
from app.models.users import User


async def get_doctor_profile(user_id: uuid.UUID) -> dict | None:
    """Get doctor profile by user ID."""
    async with get_session() as session:
        result = await session.execute(
            select(DoctorProfile, User.full_name)
            .join(User, DoctorProfile.user_id == User.id)
            .where(DoctorProfile.user_id == user_id)
        )
        row = result.first()
        if not row:
            return None
        doctor, full_name = row
        return {
            "id": str(doctor.id),
            "user_id": str(doctor.user_id),
            "full_name": full_name,
            "license_number": doctor.license_number,
            "specialty": doctor.specialty,
            "bio": doctor.bio,
            "years_of_experience": doctor.years_of_experience,
            "languages": doctor.languages or ["ar"],
            "approval_status": doctor.approval_status,
            "created_at": doctor.created_at.isoformat() if doctor.created_at else None,
        }


async def list_approved_doctors(
    search: str | None = None,
    specialty: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """List approved doctors (for patient browsing)."""
    async with get_session() as session:
        query = (
            select(DoctorProfile, User.full_name)
            .join(User, DoctorProfile.user_id == User.id)
            .where(DoctorProfile.approval_status == "approved")
        )
        count_query = (
            select(func.count())
            .select_from(DoctorProfile)
            .join(User, DoctorProfile.user_id == User.id)
            .where(DoctorProfile.approval_status == "approved")
        )

        if search:
            search_filter = User.full_name.ilike(f"%{search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if specialty:
            query = query.where(DoctorProfile.specialty.ilike(f"%{specialty}%"))
            count_query = count_query.where(DoctorProfile.specialty.ilike(f"%{specialty}%"))

        total = (await session.execute(count_query)).scalar() or 0
        result = await session.execute(
            query.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size)
        )
        rows = result.all()

        items = []
        for doctor, full_name in rows:
            items.append(
                {
                    "id": str(doctor.id),
                    "user_id": str(doctor.user_id),
                    "full_name": full_name,
                    "specialty": doctor.specialty,
                    "years_of_experience": doctor.years_of_experience,
                    "languages": doctor.languages or ["ar"],
                }
            )

        return items, total

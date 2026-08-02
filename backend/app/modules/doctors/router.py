"""Doctor router — doctor-specific endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user, require_role
from app.modules.doctors.schemas import DoctorProfileResponse
from app.modules.doctors.service import (
    get_doctor_profile,
    list_approved_doctors,
)

doctors_router = APIRouter(prefix="/doctors", tags=["doctors"])


@doctors_router.get("/me", response_model=DoctorProfileResponse)
async def my_doctor_profile(current_user: dict = Depends(require_role("doctor"))):
    """Get the current doctor's profile."""
    user_id = uuid.UUID(current_user["sub"])
    profile = await get_doctor_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return profile


@doctors_router.get("/available")
async def available_doctors(
    search: str | None = None,
    specialty: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """List approved doctors available for handoff (patient-facing)."""
    items, total = await list_approved_doctors(
        search=search, specialty=specialty, page=page, page_size=page_size
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

import uuid

from fastapi import APIRouter, Depends, status

from app.core.deps import get_current_user
from app.modules.users.schemas import (
    MeResponse,
    UpdateDoctorProfileRequest,
    UpdateMeRequest,
    UpdatePatientProfileRequest,
)
from app.modules.users.service import delete_me, get_me, update_me, update_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=MeResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return await get_me(uuid.UUID(current_user["sub"]))


@router.put("/me", response_model=MeResponse)
async def update_my_info(body: UpdateMeRequest, current_user: dict = Depends(get_current_user)):
    return await update_me(uuid.UUID(current_user["sub"]), body.model_dump(exclude_none=True))


@router.patch("/me/profile", response_model=MeResponse)
async def update_my_profile(
    body: UpdatePatientProfileRequest | UpdateDoctorProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    return await update_profile(
        uuid.UUID(current_user["sub"]),
        current_user["role"],
        body.model_dump(exclude_none=True),
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(current_user: dict = Depends(get_current_user)):
    await delete_me(uuid.UUID(current_user["sub"]))

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.deps import get_current_user, limiter
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.modules.auth.service import (
    change_password as svc_change_password,
)
from app.modules.auth.service import (
    forgot_password as svc_forgot_password,
)
from app.modules.auth.service import (
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
    resend_verification,
    verify_email,
)
from app.modules.auth.service import (
    reset_password as svc_reset_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    try:
        return await register_user(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify(body: VerifyEmailRequest):
    try:
        await verify_email(body.token)
        return VerifyEmailResponse(verified=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/resend-verification", response_model=ResendVerificationResponse)
@limiter.limit("1/minute")
async def resend(request: Request, body: ResendVerificationRequest):
    await resend_verification(body.email)
    return ResendVerificationResponse(sent=True)


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    try:
        return await login_user(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    try:
        return await refresh_tokens(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, current_user: dict = Depends(get_current_user)):
    await logout_user(body.refresh_token)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        await svc_change_password(
            uuid.UUID(current_user["sub"]), body.current_password, body.new_password
        )
        return {"changed": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    await svc_forgot_password(body.email)
    return {"sent": True}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    try:
        await svc_reset_password(body.token, body.new_password)
        return {"reset": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

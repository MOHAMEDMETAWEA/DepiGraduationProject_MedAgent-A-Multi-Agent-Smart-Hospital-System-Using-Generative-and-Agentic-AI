import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.common.audit import log_action
from app.core.config import settings
from app.core.database import get_session
from app.core.email import send_email
from app.core.security import hash_password, hash_token
from app.models.auth_token import AuthToken
from app.models.doctor_profile import DoctorProfile
from app.models.users import User
from app.modules.auth.schemas import RegisterRequest, RegisterResponse


async def register_user(request: RegisterRequest) -> RegisterResponse:
    async with get_session() as session:
        # 1. Check if email already exists
        result = await session.execute(select(User).where(User.email == request.email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # 2. Create user
        user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
            phone=request.phone,
            role=request.role,
            locale=request.locale,
        )
        session.add(user)
        await session.flush()

        # 3. If doctor, create doctor profile (pending approval)
        if request.role == "doctor":
            profile = DoctorProfile(
                user_id=user.id,
                license_number=request.license_number,
                specialty=request.specialty,
            )
            session.add(profile)

        # 4. Generate verification token
        raw_token = uuid.uuid4().hex + uuid.uuid4().hex  # 64-char random
        auth_token = AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="email_verify",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        session.add(auth_token)
        await session.commit()
        log_action("user_register", user_id=user.id, resource_type="user", resource_id=user.id)

        # 5. Send verification email (non-blocking fire-and-forget)
        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
        await send_email(
            to=user.email,
            subject="Verify your MedAgent account",
            html_body=f"<p>Click the link to verify: <a href='{verify_link}'>{verify_link}</a></p>",
        )

        return RegisterResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            requires_email_verification=True,
        )


async def verify_email(raw_token: str) -> None:
    async with get_session() as session:
        token_hash = hash_token(raw_token)
        result = await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == token_hash,
                AuthToken.purpose == "email_verify",
            )
        )
        auth_token = result.scalar_one_or_none()

        if not auth_token:
            raise ValueError("Invalid or expired token")

        if auth_token.used_at is not None:
            raise ValueError("Token already used")

        if auth_token.expires_at < datetime.now(UTC):
            raise ValueError("Token expired")

        # Mark token used + verify user
        auth_token.used_at = datetime.now(UTC)
        result = await session.execute(select(User).where(User.id == auth_token.user_id))
        user = result.scalar_one()
        user.is_email_verified = True
        await session.commit()
        log_action("email_verify", user_id=user.id, resource_type="user", resource_id=user.id)


async def resend_verification(email: str) -> None:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.email == email, User.is_email_verified.is_(False))
        )
        user = result.scalar_one_or_none()
        if not user:
            return  # Always return success to prevent enumeration

        raw_token = uuid.uuid4().hex + uuid.uuid4().hex
        auth_token = AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="email_verify",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        session.add(auth_token)
        await session.commit()

        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
        await send_email(
            to=user.email,
            subject="Verify your MedAgent account",
            html_body=f"<p>Click the link to verify: <a href='{verify_link}'>{verify_link}</a></p>",
        )


async def login_user(email: str, password: str) -> dict:
    from app.core.config import settings
    from app.core.security import (
        create_access_token,
        generate_refresh_token,
        hash_token,
        verify_password,
    )
    from app.models.refresh_token import RefreshToken

    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Invalid email or password")

        # Check lockout
        if user.locked_until and user.locked_until > datetime.now(UTC):
            remaining = int((user.locked_until - datetime.now(UTC)).total_seconds() // 60)
            raise ValueError(f"Account locked. Try again in {remaining} minutes")

        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=settings.ACCOUNT_LOCKOUT_MINUTES
                )
                user.failed_login_attempts = 0
            await session.commit()
            raise ValueError("Invalid email or password")

        if not user.is_email_verified:
            raise ValueError("Email not verified")

        if not user.is_active:
            raise ValueError("Account is disabled")

        if user.role == "doctor":
            from app.models.doctor_profile import DoctorProfile

            result = await session.execute(
                select(DoctorProfile).where(DoctorProfile.user_id == user.id)
            )
            profile = result.scalar_one_or_none()
            if profile and profile.approval_status != "approved":
                raise ValueError("Doctor account not yet approved")

        # Reset lockout on success
        user.failed_login_attempts = 0
        user.locked_until = None

        # Update last login
        user.last_login_at = datetime.now(UTC)

        # Generate tokens
        access_token = create_access_token(str(user.id), user.role)
        raw_refresh = generate_refresh_token()
        refresh = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(refresh)
        await session.commit()
        log_action("user_login", user_id=user.id, resource_type="user", resource_id=user.id)

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "locale": user.locale,
            },
        }


async def refresh_tokens(raw_refresh: str) -> dict:
    from app.core.security import (
        create_access_token,
        generate_refresh_token,
        hash_token,
    )
    from app.models.refresh_token import RefreshToken

    token_hash = hash_token(raw_refresh)
    async with get_session() as session:
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        refresh = result.scalar_one_or_none()

        if not refresh or refresh.expires_at < datetime.now(UTC):
            # Token theft detection: revoke ALL user tokens
            if not refresh:
                # Token might be revoked — look it up without revoked filter
                revoked_result = await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.token_hash == token_hash,
                    )
                )
                refresh = revoked_result.scalar_one_or_none()

            if refresh:
                all_tokens = (
                    (
                        await session.execute(
                            select(RefreshToken).where(RefreshToken.user_id == refresh.user_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                for t in all_tokens:
                    t.revoked_at = datetime.now(UTC)
                await session.commit()
            raise ValueError("Invalid or expired refresh token")

        # Revoke old token (rotation)
        refresh.revoked_at = datetime.now(UTC)

        # Get user
        result = await session.execute(select(User).where(User.id == refresh.user_id))
        user = result.scalar_one()

        # Issue new pair
        access_token = create_access_token(str(user.id), user.role)
        new_raw = generate_refresh_token()
        new_refresh = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_raw),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(new_refresh)
        await session.commit()

        return {"access_token": access_token, "refresh_token": new_raw}


async def logout_user(raw_refresh: str) -> None:
    from app.models.refresh_token import RefreshToken

    token_hash = hash_token(raw_refresh)
    async with get_session() as session:
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        refresh = result.scalar_one_or_none()
        if refresh:
            refresh.revoked_at = datetime.now(UTC)
            await session.commit()
            log_action("user_logout", user_id=refresh.user_id, resource_type="refresh_token")


async def change_password(user_id: uuid.UUID, current_password: str, new_password: str) -> None:
    from app.core.security import hash_password, verify_password
    from app.models.refresh_token import RefreshToken

    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        user.hashed_password = hash_password(new_password)

        # Revoke all refresh tokens for security
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for token in result.scalars().all():
            token.revoked_at = datetime.now(UTC)

        await session.commit()
        log_action(
            "password_change",
            user_id=user_id,
            resource_type="user",
            resource_id=user_id,
        )


async def forgot_password(email: str) -> None:
    """Send password reset email. Always returns success to prevent enumeration."""
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user:
            return  # Silent success

        raw_token = uuid.uuid4().hex + uuid.uuid4().hex
        auth_token = AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="password_reset",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(auth_token)
        await session.commit()
        log_action(
            "password_reset_request",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
        )

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        await send_email(
            to=user.email,
            subject="Reset your MedAgent password",
            html_body=f"<p>Click to reset: <a href='{reset_link}'>{reset_link}</a></p>",
        )


async def reset_password(raw_token: str, new_password: str) -> None:
    from app.models.refresh_token import RefreshToken

    async with get_session() as session:
        token_hash = hash_token(raw_token)
        result = await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == token_hash,
                AuthToken.purpose == "password_reset",
            )
        )
        auth_token = result.scalar_one_or_none()

        if (
            not auth_token
            or auth_token.used_at is not None
            or auth_token.expires_at < datetime.now(UTC)
        ):
            raise ValueError("Invalid or expired token")

        user = await session.get(User, auth_token.user_id)
        if not user:
            raise ValueError("User not found")

        user.hashed_password = hash_password(new_password)
        auth_token.used_at = datetime.now(UTC)

        # Revoke all refresh tokens
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for t in result.scalars().all():
            t.revoked_at = datetime.now(UTC)

        await session.commit()
        log_action("password_reset", user_id=user.id, resource_type="user", resource_id=user.id)

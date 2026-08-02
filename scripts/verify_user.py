"""Manual user verification helper — bypasses SMTP for demos.

Use cases:
  * SMTP is down / Gmail App Password isn't cooperating
  * Onboarding the team for a live demo
  * Local development on a fresh DB

Usage (from repo root):
  docker compose exec backend /app/.venv/bin/python /app/scripts/verify_user.py <email>
  docker compose exec backend /app/.venv/bin/python /app/scripts/verify_user.py --list-recent
  docker compose exec backend /app/.venv/bin/python /app/scripts/verify_user.py --link <email>

  <email>             flip is_email_verified=True so the user can log in
  --list-recent       show the last 10 registered users + verification status
  --link <email>      regenerate a fresh verify token + print the URL
                      (useful if you want the verify-email flow to actually
                      run, just without sending the email)
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Same trick seed_kb.py uses — make ``app`` importable when this file is
# invoked as ``python /app/scripts/verify_user.py`` (cwd != project root).
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import desc, select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import get_session  # noqa: E402
from app.core.security import hash_token  # noqa: E402
from app.models.auth_token import AuthToken  # noqa: E402
from app.models.users import User  # noqa: E402


async def verify_by_email(email: str) -> int:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            print(f"❌ No user with email {email!r}")
            return 1
        if user.is_email_verified:
            print(f"✓ {user.email} is already verified (role={user.role})")
            return 0
        user.is_email_verified = True
        await session.commit()
        print(f"✅ {user.email} verified (role={user.role}). User can now log in.")
        return 0


async def list_recent() -> int:
    async with get_session() as session:
        result = await session.execute(
            select(User).order_by(desc(User.created_at)).limit(10)
        )
        users = result.scalars().all()
        if not users:
            print("(no users yet)")
            return 0
        print(f"{'EMAIL':<40} {'ROLE':<10} {'VERIFIED':<10} {'CREATED'}")
        print("-" * 90)
        for u in users:
            verified = "✅" if u.is_email_verified else "❌"
            created = u.created_at.strftime("%Y-%m-%d %H:%M")
            print(f"{u.email:<40} {u.role:<10} {verified:<10} {created}")
        return 0


async def make_link(email: str) -> int:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            print(f"❌ No user with email {email!r}")
            return 1

        raw_token = uuid.uuid4().hex + uuid.uuid4().hex  # same recipe as service.py
        auth_token = AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            purpose="email_verify",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        session.add(auth_token)
        await session.commit()

        link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
        print(f"📨 Fresh verify link for {user.email} (valid 24h):\n   {link}")
        return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2

    if args[0] == "--list-recent":
        return asyncio.run(list_recent())
    if args[0] == "--link":
        if len(args) < 2:
            print("Usage: verify_user.py --link <email>")
            return 2
        return asyncio.run(make_link(args[1]))
    return asyncio.run(verify_by_email(args[0]))


if __name__ == "__main__":
    sys.exit(main())

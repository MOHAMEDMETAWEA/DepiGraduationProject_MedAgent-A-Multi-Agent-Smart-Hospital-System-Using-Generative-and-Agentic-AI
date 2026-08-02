"""Admin router — dashboard, user/doctor management, safety, audit."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.common.audit_chain import GENESIS_HASH, compute_hash
from app.core.database import get_session
from app.core.deps import require_role
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.models.doctor_profile import DoctorProfile
from app.models.safety_assessment import SafetyAssessment
from app.models.users import User

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/dashboard")
async def dashboard(current_user: dict = Depends(require_role("admin"))):
    """Admin dashboard stats."""
    async with get_session() as session:
        total_users = (await session.execute(select(func.count()).select_from(User))).scalar() or 0

        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        active_today = (
            await session.execute(
                select(func.count())
                .select_from(Conversation)
                .where(Conversation.created_at >= today)
            )
        ).scalar() or 0

        week_ago = datetime.now(UTC) - timedelta(days=7)
        safety_incidents = (
            await session.execute(
                select(func.count())
                .select_from(Conversation)
                .where(
                    Conversation.status == "flagged_for_review",
                    Conversation.updated_at >= week_ago,
                )
            )
        ).scalar() or 0

        pending_doctors = (
            await session.execute(
                select(func.count())
                .select_from(DoctorProfile)
                .where(DoctorProfile.approval_status == "pending")
            )
        ).scalar() or 0

        return {
            "total_users": total_users,
            "active_today": active_today,
            "safety_incidents_this_week": safety_incidents,
            "pending_doctors": pending_doctors,
            "system_health": "ok",
        }


@admin_router.get("/users")
async def list_users(
    role: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(require_role("admin")),
):
    """List all users with filters."""
    async with get_session() as session:
        query = select(User)
        count_query = select(func.count()).select_from(User)

        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if search:
            query = query.where(
                User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
            )
            count_query = count_query.where(
                User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
            )

        total = (await session.execute(count_query)).scalar() or 0
        result = await session.execute(
            query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        users = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role,
                    "is_active": u.is_active,
                    "is_email_verified": u.is_email_verified,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@admin_router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    body: dict,
    current_user: dict = Depends(require_role("admin")),
):
    """Activate/deactivate user or change role."""
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if "is_active" in body:
            user.is_active = body["is_active"]
        if "role" in body:
            user.role = body["role"]

        await session.commit()
        return {"updated": True}


@admin_router.get("/doctors/pending")
async def pending_doctors(current_user: dict = Depends(require_role("admin"))):
    """List doctors awaiting approval."""
    async with get_session() as session:
        result = await session.execute(
            select(DoctorProfile).where(DoctorProfile.approval_status == "pending")
        )
        doctors = result.scalars().all()
        return {
            "items": [
                {
                    "id": str(d.id),
                    "user_id": str(d.user_id),
                    "license_number": d.license_number,
                    "specialty": d.specialty,
                    "created_at": d.created_at.isoformat(),
                }
                for d in doctors
            ]
        }


@admin_router.post("/doctors/{doctor_id}/approve")
async def approve_doctor(
    doctor_id: uuid.UUID,
    current_user: dict = Depends(require_role("admin")),
):
    """Approve a doctor."""
    async with get_session() as session:
        doctor = await session.get(DoctorProfile, doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        doctor.approval_status = "approved"
        doctor.approved_by = uuid.UUID(current_user["sub"])
        doctor.approved_at = datetime.now(UTC)
        await session.commit()
        return {"approved": True}


@admin_router.post("/doctors/{doctor_id}/reject")
async def reject_doctor(
    doctor_id: uuid.UUID,
    body: dict,
    current_user: dict = Depends(require_role("admin")),
):
    """Reject a doctor with reason."""
    async with get_session() as session:
        doctor = await session.get(DoctorProfile, doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        doctor.approval_status = "rejected"
        doctor.rejection_reason = body.get("reason", "")
        await session.commit()
        return {"rejected": True}


@admin_router.get("/safety-incidents")
async def safety_incidents(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(require_role("admin")),
):
    """List conversations flagged for review."""
    async with get_session() as session:
        query = (
            select(Conversation)
            .where(Conversation.status == "flagged_for_review")
            .order_by(Conversation.updated_at.desc())
        )
        count_query = (
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.status == "flagged_for_review")
        )
        total = (await session.execute(count_query)).scalar() or 0
        result = await session.execute(query.offset((page - 1) * page_size).limit(page_size))
        convs = result.scalars().all()
        return {
            "items": [
                {
                    "id": str(c.id),
                    "title": c.title,
                    "triage_level": c.triage_level,
                    "created_at": c.created_at.isoformat(),
                }
                for c in convs
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@admin_router.get("/audit-logs")
async def audit_logs(
    user_id: str | None = None,
    action: str | None = None,
    page: int = 1,
    page_size: int = 50,
    current_user: dict = Depends(require_role("admin")),
):
    """View audit logs with filters."""
    async with get_session() as session:
        query = select(AuditLog).order_by(AuditLog.sequence.desc())
        count_query = select(func.count()).select_from(AuditLog)

        if user_id:
            query = query.where(AuditLog.user_id == uuid.UUID(user_id))
            count_query = count_query.where(AuditLog.user_id == uuid.UUID(user_id))
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)

        total = (await session.execute(count_query)).scalar() or 0
        result = await session.execute(query.offset((page - 1) * page_size).limit(page_size))
        logs = result.scalars().all()
        return {
            "items": [
                {
                    "id": str(log.id),
                    "sequence": log.sequence,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@admin_router.get("/audit-verify")
async def audit_verify(current_user: dict = Depends(require_role("admin"))):
    """Verify audit chain integrity."""
    async with get_session() as session:
        result = await session.execute(select(AuditLog).order_by(AuditLog.sequence))
        rows = result.scalars().all()

        if not rows:
            return {"ok": True, "last_sequence": 0, "broken_at": None}

        expected_previous = GENESIS_HASH
        for row in rows:
            computed = compute_hash(
                sequence=row.sequence,
                user_id=row.user_id,
                action=row.action,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                details=row.details,
                ip_address=str(row.ip_address) if row.ip_address else None,
                user_agent=row.user_agent,
                created_at=row.created_at,
                previous_hash=expected_previous,
            )
            if computed != row.current_hash:
                return {"ok": False, "last_sequence": row.sequence, "broken_at": row.sequence}
            expected_previous = row.current_hash

        return {"ok": True, "last_sequence": rows[-1].sequence if rows else 0, "broken_at": None}


@admin_router.get("/safety-stats")
async def safety_stats(
    current_user: dict = Depends(require_role("admin")),
):
    """Safety statistics: hallucination rate, citation rate, uncertainty distribution, triage inconsistencies."""
    async with get_session() as session:
        # Total safety assessments
        total_result = await session.execute(select(func.count()).select_from(SafetyAssessment))
        total = total_result.scalar() or 0

        if total == 0:
            return {
                "total_assessments": 0,
                "hallucination_avg": None,
                "hallucination_rate": None,
                "citation_avg": None,
                "citation_rate": None,
                "uncertainty_distribution": {},
                "triage_inconsistencies": 0,
                "forbidden_phrase_rewrites_total": 0,
                "flagged_conversations": 0,
            }

        # Average hallucination score
        h_avg = (
            await session.execute(
                select(func.avg(SafetyAssessment.hallucination_score)).where(
                    SafetyAssessment.hallucination_score.isnot(None)
                )
            )
        ).scalar()

        # Hallucination rate (score > threshold 0.3)
        h_high = (
            await session.execute(
                select(func.count()).where(SafetyAssessment.hallucination_score > 0.3)
            )
        ).scalar() or 0

        # Average citation completeness
        c_avg = (
            await session.execute(
                select(func.avg(SafetyAssessment.citation_completeness)).where(
                    SafetyAssessment.citation_completeness.isnot(None)
                )
            )
        ).scalar()

        # Citation rate (completeness > 0.5)
        c_good = (
            await session.execute(
                select(func.count()).where(SafetyAssessment.citation_completeness > 0.5)
            )
        ).scalar() or 0

        # Uncertainty distribution
        uncertainty_result = await session.execute(
            select(
                SafetyAssessment.uncertainty_band,
                func.count(SafetyAssessment.id),
            )
            .where(SafetyAssessment.uncertainty_band.isnot(None))
            .group_by(SafetyAssessment.uncertainty_band)
        )
        uncertainty_dist = {row[0]: row[1] for row in uncertainty_result}

        # Triage inconsistencies
        inconsistent = (
            await session.execute(
                select(func.count()).where(SafetyAssessment.triage_consistent.is_(False))
            )
        ).scalar() or 0

        # Forbidden phrase rewrites total
        rewrites = (
            await session.execute(select(func.sum(SafetyAssessment.forbidden_phrases_rewritten)))
        ).scalar() or 0

        # Flagged conversations
        flagged = (
            await session.execute(
                select(func.count())
                .select_from(Conversation)
                .where(Conversation.status == "flagged_for_review")
            )
        ).scalar() or 0

        return {
            "total_assessments": total,
            "hallucination_avg": round(float(h_avg), 4) if h_avg else None,
            "hallucination_rate": round(h_high / total, 4) if total else 0,
            "citation_avg": round(float(c_avg), 4) if c_avg else None,
            "citation_rate": round(c_good / total, 4) if total else 0,
            "uncertainty_distribution": uncertainty_dist,
            "triage_inconsistencies": inconsistent,
            "forbidden_phrase_rewrites_total": rewrites,
            "flagged_conversations": flagged,
        }

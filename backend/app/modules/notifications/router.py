import uuid

from fastapi import APIRouter, Depends, Query, Request

from app.core.deps import get_current_user, limiter
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
    ScheduleFollowUpRequest,
    ScheduleResponse,
    TriggerFollowUpResponse,
)
from app.modules.notifications.service import (
    get_user_notifications,
    process_due_notifications,
    schedule_follow_up,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/follow-up/schedule", response_model=ScheduleResponse)
@limiter.limit("10/minute")
async def api_schedule_follow_up(
    request: Request,
    body: ScheduleFollowUpRequest,
    current_user: dict = Depends(get_current_user),
):
    """Schedule a follow-up email for a completed or active conversation."""
    from datetime import UTC, datetime, timedelta

    notification_id = await schedule_follow_up(
        conversation_id=body.conversation_id,
        delay_hours=body.delay_hours,
        template=body.template,
        reason=body.reason,
    )

    if not notification_id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Conversation or user not found",
        )

    return ScheduleResponse(
        notification_id=notification_id,
        scheduled_for=datetime.now(UTC) + timedelta(hours=body.delay_hours),
        status="queued",
    )


@router.get("", response_model=NotificationListResponse)
async def api_list_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List notification history for the current user."""
    user_id = uuid.UUID(current_user["sub"])
    notifications, total = await get_user_notifications(user_id=user_id, limit=limit, offset=offset)

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id,
                channel=n.channel,
                template=n.template,
                recipient=n.recipient,
                status=n.status,
                sent_at=n.sent_at,
                error_message=n.error_message,
                metadata=n.extra_meta,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        total=total,
    )


@router.post("/trigger", response_model=TriggerFollowUpResponse)
async def api_trigger_follow_ups(
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger processing of all due notifications (admin/debug endpoint)."""
    result = await process_due_notifications()
    return TriggerFollowUpResponse(**result)

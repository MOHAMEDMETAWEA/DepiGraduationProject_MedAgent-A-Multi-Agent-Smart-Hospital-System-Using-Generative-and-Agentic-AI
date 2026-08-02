import uuid
from datetime import datetime

from pydantic import BaseModel


class ScheduleFollowUpRequest(BaseModel):
    conversation_id: uuid.UUID
    delay_hours: int = 24
    template: str = "follow_up"
    reason: str | None = None


class ScheduleSafetyFollowUpRequest(BaseModel):
    conversation_id: uuid.UUID
    delay_hours: int = 24


class ScheduleResponse(BaseModel):
    notification_id: uuid.UUID
    scheduled_for: datetime
    status: str = "queued"


class NotificationResponse(BaseModel):
    id: uuid.UUID
    channel: str
    template: str
    recipient: str
    status: str
    sent_at: datetime | None = None
    error_message: str | None = None
    metadata: dict | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int


class TriggerFollowUpResponse(BaseModel):
    processed: int
    sent: int
    failed: int

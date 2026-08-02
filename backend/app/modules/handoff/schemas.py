"""Handoff schemas — doctor handoff summaries."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

HandoffStatus = Literal["new", "acknowledged", "in_progress", "reviewed", "closed"]


class HandoffCreate(BaseModel):
    """Request to generate a handoff summary."""

    conversation_id: uuid.UUID


class HandoffSend(BaseModel):
    """Request to send handoff to a specific doctor."""

    doctor_user_id: uuid.UUID
    message: str | None = Field(default=None, max_length=500)


class HandoffReview(BaseModel):
    """Doctor reviews a received handoff."""

    notes: str | None = Field(default=None, max_length=2000)


class HandoffStatusUpdate(BaseModel):
    """Doctor advances handoff workflow state."""

    status: Literal["acknowledged", "in_progress", "reviewed", "closed"]
    notes: str | None = Field(default=None, max_length=2000)


class HandoffResponse(BaseModel):
    """Handoff summary returned to client."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    patient_user_id: uuid.UUID
    patient_name: str | None = None
    doctor_user_id: uuid.UUID | None = None
    status: HandoffStatus = "new"
    priority: int = 0
    target_specialty: str | None = None
    target_language: str | None = None
    auto_routed: bool = False
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    reviewed_at: datetime | None = None
    closed_at: datetime | None = None
    doctor_private_notes: str | None = None
    summary_markdown: str
    pdf_url: str | None = None
    created_at: datetime
    updated_at: datetime


class HandoffListResponse(BaseModel):
    """Paginated list of handoffs."""

    items: list[HandoffResponse]
    total: int
    page: int = 1
    page_size: int = 20


class InboxCountResponse(BaseModel):
    """Per-status counts for the doctor inbox."""

    new: int = 0
    acknowledged: int = 0
    in_progress: int = 0
    reviewed: int = 0
    closed: int = 0
    total: int = 0

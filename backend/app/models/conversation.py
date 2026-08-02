import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    triage_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    triage_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_diagnosis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    differential_diagnoses: Mapped[list | None] = mapped_column(JSONB, server_default="[]")
    red_flags_detected: Mapped[list] = mapped_column(JSONB, default=list)
    language: Mapped[str] = mapped_column(String(5), default="ar", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class HandoffSummary(Base):
    __tablename__ = "handoff_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    doctor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="new")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    target_specialty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(5), nullable=True)
    auto_routed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    doctor_private_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    exports = relationship("HandoffExport", back_populates="handoff")

    __table_args__ = (
        Index(
            "idx_handoff_doctor_inbox",
            "doctor_user_id",
            "status",
            text("priority DESC"),
            text("sent_at DESC"),
        ),
        Index("idx_handoff_status", "status"),
    )

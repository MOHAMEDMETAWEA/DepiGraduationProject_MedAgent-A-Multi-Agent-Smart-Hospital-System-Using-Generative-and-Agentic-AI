"""
HandoffExports model — تصديرات التلخيص (FHIR / HL7 / PDF)
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HandoffExport(Base):
    __tablename__ = "handoff_exports"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    handoff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("handoff_summaries.id", ondelete="CASCADE"),
        nullable=False,
    )
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    content_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_inline: Mapped[str | None] = mapped_column(Text, nullable=True)
    bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        CheckConstraint(
            "format IN ('fhir', 'hl7', 'pdf')",
            name="ck_handoff_export_format",
        ),
        UniqueConstraint("handoff_id", "format", name="uq_handoff_export_format"),
    )

    handoff = relationship("HandoffSummary", back_populates="exports")

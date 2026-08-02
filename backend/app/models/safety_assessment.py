import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SafetyAssessment(Base):
    __tablename__ = "safety_assessments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    hallucination_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    citation_completeness: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    uncertainty_band: Mapped[str | None] = mapped_column(String(20), nullable=True)

    calibration_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    forbidden_phrases_rewritten: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    triage_consistent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # NOW() في Postgres — توقيت الخادم مش توقيت بايثون
    )

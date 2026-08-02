import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.encryption import is_encryption_enabled
from app.models._types import EncryptedString
from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Plaintext column kept for backward-compat / encryption-disabled mode.
    # When PHI_ENCRYPTION_ENABLED=true, writes go to encrypted_content and content stays empty.
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    encrypted_content: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    tool_calls: Mapped[list] = mapped_column(JSONB, default=list)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_meta: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def text(self) -> str:
        """Read-side accessor: prefers decrypted content, falls back to plaintext."""
        if self.encrypted_content is not None:
            return self.encrypted_content
        return self.content or ""

    @classmethod
    def from_payload(
        cls,
        *,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        **kwargs,
    ) -> "Message":
        """Factory that routes the message body to the right column based on encryption state."""
        if is_encryption_enabled():
            return cls(
                conversation_id=conversation_id,
                role=role,
                content="",
                encrypted_content=content,
                **kwargs,
            )
        return cls(
            conversation_id=conversation_id,
            role=role,
            content=content,
            encrypted_content=None,
            **kwargs,
        )

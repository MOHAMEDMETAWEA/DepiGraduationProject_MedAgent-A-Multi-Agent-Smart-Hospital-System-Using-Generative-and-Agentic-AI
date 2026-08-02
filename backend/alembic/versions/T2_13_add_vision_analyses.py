"""T2.13 — Add vision_analyses table

Revision ID: a1b2c3d4e5f6
Revises: 0193202de7ca
Create Date: 2026-05-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "7774aebfe2b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vision_analyses",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("image_kind", sa.String(20), nullable=False, server_default="other"),
        sa.Column("analysis_markdown", sa.Text, nullable=True),
        sa.Column("findings", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("urgency", sa.String(20), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("disclaimer_shown", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_vision_conv", "vision_analyses", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("idx_vision_conv", table_name="vision_analyses")
    op.drop_table("vision_analyses")

"""T2.5.01 — Add safety_assessments table for post-LLM hallucination verification

Revision ID: b2c3d4e5f6a7
Revises: T2_13_add_vision_analyses
Create Date: 2026-05-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create safety_assessments table — stores hallucination check results per message."""
    op.create_table(
        "safety_assessments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("hallucination_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("citation_completeness", sa.Numeric(4, 3), nullable=True),
        sa.Column("uncertainty_band", sa.String(20), nullable=True),
        sa.Column("calibration_metadata", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("forbidden_phrases_rewritten", sa.Integer, nullable=False, server_default="0"),
        sa.Column("triage_consistent", sa.Boolean, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_safety_msg", "safety_assessments", ["message_id"])


def downgrade() -> None:
    """Drop safety_assessments table."""
    op.drop_index("idx_safety_msg", table_name="safety_assessments")
    op.drop_table("safety_assessments")

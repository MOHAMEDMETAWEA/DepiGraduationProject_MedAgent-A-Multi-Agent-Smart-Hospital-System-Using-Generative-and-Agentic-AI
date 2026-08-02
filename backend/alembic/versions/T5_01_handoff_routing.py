"""T5_01 — Handoff routing & inbox status

Adds status workflow, priority, target_specialty/language fields to
handoff_summaries; is_available flag to doctor_profiles. Backfills
status from reviewed_at, priority from conversations.triage_level,
and target_language from conversations.language. Adds composite index
for the doctor inbox query path.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # handoff_summaries: routing & status workflow
    op.add_column(
        "handoff_summaries",
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
    )
    op.add_column(
        "handoff_summaries",
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "handoff_summaries",
        sa.Column("target_specialty", sa.String(50), nullable=True),
    )
    op.add_column(
        "handoff_summaries",
        sa.Column("target_language", sa.String(5), nullable=True),
    )
    op.add_column(
        "handoff_summaries",
        sa.Column("auto_routed", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "handoff_summaries",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "handoff_summaries",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # doctor_profiles: availability flag
    op.add_column(
        "doctor_profiles",
        sa.Column("is_available", sa.Boolean, nullable=False, server_default=sa.true()),
    )

    # Backfill from existing data
    op.execute(
        "UPDATE handoff_summaries "
        "SET status = CASE WHEN reviewed_at IS NOT NULL THEN 'reviewed' ELSE 'new' END"
    )
    op.execute(
        "UPDATE handoff_summaries hs "
        "SET priority = CASE c.triage_level "
        "WHEN 'emergency' THEN 100 "
        "WHEN 'urgent' THEN 70 "
        "WHEN 'routine' THEN 30 "
        "ELSE 0 END, "
        "target_language = c.language "
        "FROM conversations c "
        "WHERE hs.conversation_id = c.id"
    )

    # Indexes for inbox queries
    op.create_index(
        "idx_handoff_doctor_inbox",
        "handoff_summaries",
        ["doctor_user_id", "status", sa.text("priority DESC"), sa.text("sent_at DESC")],
    )
    op.create_index("idx_handoff_status", "handoff_summaries", ["status"])
    op.create_index("idx_doctor_available", "doctor_profiles", ["is_available"])


def downgrade() -> None:
    op.drop_index("idx_doctor_available", table_name="doctor_profiles")
    op.drop_index("idx_handoff_status", table_name="handoff_summaries")
    op.drop_index("idx_handoff_doctor_inbox", table_name="handoff_summaries")

    op.drop_column("doctor_profiles", "is_available")

    op.drop_column("handoff_summaries", "closed_at")
    op.drop_column("handoff_summaries", "acknowledged_at")
    op.drop_column("handoff_summaries", "auto_routed")
    op.drop_column("handoff_summaries", "target_language")
    op.drop_column("handoff_summaries", "target_specialty")
    op.drop_column("handoff_summaries", "priority")
    op.drop_column("handoff_summaries", "status")

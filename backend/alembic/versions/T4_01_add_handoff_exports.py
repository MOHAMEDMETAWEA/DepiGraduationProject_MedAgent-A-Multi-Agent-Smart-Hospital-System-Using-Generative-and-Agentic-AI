"""T4_01 — Add handoff_exports table

Stores FHIR/HL7/PDF export artifacts for each handoff summary.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "handoff_exports",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "handoff_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("handoff_summaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("content_url", sa.String(500), nullable=True),
        sa.Column("content_inline", sa.Text, nullable=True),
        sa.Column("bytes", sa.Integer, nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("handoff_id", "format", name="uq_handoff_export_format"),
    )
    op.create_index("idx_handoff_exports_handoff", "handoff_exports", ["handoff_id"])


def downgrade() -> None:
    op.drop_index("idx_handoff_exports_handoff", table_name="handoff_exports")
    op.drop_table("handoff_exports")

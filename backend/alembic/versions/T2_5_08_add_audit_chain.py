"""T2.5.08 — Add audit hash chain columns (tamper-evident)

Revision ID: d4e5f6a7b8c9
Revises: T2_5_07_add_encrypted_columns
Create Date: 2026-05-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add hash chain columns to audit_logs."""
    op.add_column("audit_logs", sa.Column("sequence", sa.BigInteger, nullable=True))
    op.add_column("audit_logs", sa.Column("previous_hash", sa.String(64), nullable=True))
    op.add_column("audit_logs", sa.Column("current_hash", sa.String(64), nullable=True))

    # Set defaults on existing rows
    op.execute(
        "UPDATE audit_logs SET previous_hash = 'genesis', current_hash = 'genesis' WHERE previous_hash IS NULL"
    )

    # Make NOT NULL after filling
    op.alter_column("audit_logs", "previous_hash", nullable=False)
    op.alter_column("audit_logs", "current_hash", nullable=False)

    op.create_unique_constraint("uq_audit_sequence", "audit_logs", ["sequence"])
    op.create_index("idx_audit_sequence", "audit_logs", ["sequence"])


def downgrade() -> None:
    """Remove hash chain columns."""
    op.drop_index("idx_audit_sequence", table_name="audit_logs")
    op.drop_constraint("uq_audit_sequence", table_name="audit_logs")
    op.drop_column("audit_logs", "current_hash")
    op.drop_column("audit_logs", "previous_hash")
    op.drop_column("audit_logs", "sequence")

"""T2.5.07 — Add encrypted_content columns for PHI encryption

Revision ID: c3d4e5f6a7b8
Revises: T2_5_01_add_safety_assessments
Create Date: 2026-05-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add encrypted BYTEA columns for PHI fields."""
    # messages
    op.add_column("messages", sa.Column("encrypted_content", sa.LargeBinary, nullable=True))

    # vision_analyses
    op.add_column("vision_analyses", sa.Column("encrypted_analysis", sa.LargeBinary, nullable=True))


def downgrade() -> None:
    """Remove encrypted columns."""
    op.drop_column("vision_analyses", "encrypted_analysis")
    op.drop_column("messages", "encrypted_content")

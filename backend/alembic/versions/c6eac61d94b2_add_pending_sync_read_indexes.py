"""add_pending_sync_read_indexes

Revision ID: c6eac61d94b2
Revises: b3f8c2e91a45
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c6eac61d94b2"
down_revision: Union[str, Sequence[str], None] = "b3f8c2e91a45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_pending_sync_changes_batch_status",
        "pending_sync_changes",
        ["batch_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_pending_sync_changes_status",
        "pending_sync_changes",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_sync_batches_status_created_at_id",
        "sync_batches",
        ["status", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_sync_batches_status_created_at_id", table_name="sync_batches")
    op.drop_index("ix_pending_sync_changes_status", table_name="pending_sync_changes")
    op.drop_index("ix_pending_sync_changes_batch_status", table_name="pending_sync_changes")

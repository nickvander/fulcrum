"""add_catalog_imports

Revision ID: e2f1a9b73c40
Revises: 4d2c8a01b9f3
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f1a9b73c40"
down_revision: Union[str, Sequence[str], None] = "4d2c8a01b9f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_catalog_imports_id"), "catalog_imports", ["id"], unique=False)
    op.create_index(
        op.f("ix_catalog_imports_created_at"),
        "catalog_imports",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catalog_imports_status"),
        "catalog_imports",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catalog_imports_supplier_id"),
        "catalog_imports",
        ["supplier_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_catalog_imports_supplier_id"), table_name="catalog_imports")
    op.drop_index(op.f("ix_catalog_imports_status"), table_name="catalog_imports")
    op.drop_index(op.f("ix_catalog_imports_created_at"), table_name="catalog_imports")
    op.drop_index(op.f("ix_catalog_imports_id"), table_name="catalog_imports")
    op.drop_table("catalog_imports")

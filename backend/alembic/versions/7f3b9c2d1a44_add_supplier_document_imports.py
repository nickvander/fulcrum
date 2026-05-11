"""add_supplier_document_imports

Revision ID: 7f3b9c2d1a44
Revises: 2b7f0c8d9e12
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f3b9c2d1a44"
down_revision: Union[str, Sequence[str], None] = "2b7f0c8d9e12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supplier_document_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("purchase_order_id", sa.Integer(), nullable=True),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_document_imports_id"), "supplier_document_imports", ["id"], unique=False)
    op.create_index(
        op.f("ix_supplier_document_imports_created_at"),
        "supplier_document_imports",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_document_imports_purchase_order_id"),
        "supplier_document_imports",
        ["purchase_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_document_imports_status"),
        "supplier_document_imports",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_document_imports_supplier_id"),
        "supplier_document_imports",
        ["supplier_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_document_imports_supplier_id"), table_name="supplier_document_imports")
    op.drop_index(op.f("ix_supplier_document_imports_status"), table_name="supplier_document_imports")
    op.drop_index(op.f("ix_supplier_document_imports_purchase_order_id"), table_name="supplier_document_imports")
    op.drop_index(op.f("ix_supplier_document_imports_created_at"), table_name="supplier_document_imports")
    op.drop_index(op.f("ix_supplier_document_imports_id"), table_name="supplier_document_imports")
    op.drop_table("supplier_document_imports")

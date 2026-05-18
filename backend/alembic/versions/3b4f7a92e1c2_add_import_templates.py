"""add_import_templates

Revision ID: 3b4f7a92e1c2
Revises: e2f1a9b73c40
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3b4f7a92e1c2"
down_revision: Union[str, Sequence[str], None] = "e2f1a9b73c40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("column_map", sa.JSON(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "created_by_id", "source_type", "name",
            name="uq_import_template_owner_name",
        ),
    )
    op.create_index(op.f("ix_import_templates_id"), "import_templates", ["id"], unique=False)
    op.create_index(op.f("ix_import_templates_source_type"), "import_templates", ["source_type"], unique=False)
    op.create_index(op.f("ix_import_templates_created_by_id"), "import_templates", ["created_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_import_templates_created_by_id"), table_name="import_templates")
    op.drop_index(op.f("ix_import_templates_source_type"), table_name="import_templates")
    op.drop_index(op.f("ix_import_templates_id"), table_name="import_templates")
    op.drop_table("import_templates")

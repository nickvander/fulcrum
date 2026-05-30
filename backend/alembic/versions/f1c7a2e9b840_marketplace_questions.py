"""marketplace_questions table (buyer Q&A + SLA)

Persist buyer pre-sale questions (MercadoLibre `/questions`) so the Q&A
reports surface can show unanswered questions + response-time SLA from
the DB (no live API call needed at render time). Idempotent on
(credential_id, external_question_id).

Revision ID: f1c7a2e9b840
Revises: e6b3d9a8c741
Create Date: 2026-05-30 21:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f1c7a2e9b840"
down_revision: Union[str, Sequence[str], None] = "e6b3d9a8c741"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplace_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("marketplace_id", sa.Integer(), nullable=True),
        sa.Column("external_question_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("buyer_id", sa.String(), nullable=True),
        sa.Column("question_text", sa.String(), nullable=True),
        sa.Column("answer_text", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["credential_id"], ["marketplace_credentials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["marketplace_id"], ["marketplaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "credential_id", "external_question_id",
            name="uq_marketplace_questions_cred_extid",
        ),
    )
    op.create_index(op.f("ix_marketplace_questions_id"), "marketplace_questions", ["id"])
    op.create_index(
        op.f("ix_marketplace_questions_credential_id"),
        "marketplace_questions", ["credential_id"],
    )
    op.create_index(
        op.f("ix_marketplace_questions_external_question_id"),
        "marketplace_questions", ["external_question_id"],
    )
    op.create_index(op.f("ix_marketplace_questions_status"), "marketplace_questions", ["status"])
    op.create_index(op.f("ix_marketplace_questions_asked_at"), "marketplace_questions", ["asked_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_marketplace_questions_asked_at"), table_name="marketplace_questions")
    op.drop_index(op.f("ix_marketplace_questions_status"), table_name="marketplace_questions")
    op.drop_index(op.f("ix_marketplace_questions_external_question_id"), table_name="marketplace_questions")
    op.drop_index(op.f("ix_marketplace_questions_credential_id"), table_name="marketplace_questions")
    op.drop_index(op.f("ix_marketplace_questions_id"), table_name="marketplace_questions")
    op.drop_table("marketplace_questions")

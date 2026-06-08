"""FP-06 P2: cfdi_documents.idempotency_key (nota-de-crédito idempotency)

Adds a nullable, unique ``idempotency_key`` so issuing a nota de crédito (egreso)
is idempotent — a retry with the same key returns the existing document instead
of stamping a second credit note. Ingreso rows leave it NULL.

Additive; no backfill. Builds linearly on the sole head ``e1a2b3c4d5f6``.

Revision ID: f2b3c4d5e6a7
Revises: e1a2b3c4d5f6
Create Date: 2026-06-08 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2b3c4d5e6a7"
down_revision: Union[str, Sequence[str], None] = "e1a2b3c4d5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cfdi_documents",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_cfdi_documents_idempotency_key",
        "cfdi_documents",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_cfdi_documents_idempotency_key", table_name="cfdi_documents")
    op.drop_column("cfdi_documents", "idempotency_key")

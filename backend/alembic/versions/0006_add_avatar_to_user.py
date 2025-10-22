"""Add avatar to user model

Revision ID: 0006_add_avatar_to_user
Revises: 0005_user_audit_log
Create Date: 2025-10-20 00:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_add_avatar_to_user'
down_revision = '0005_user_audit_log'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add avatar column to users table
    op.add_column('users', sa.Column('avatar', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove avatar column from users table
    op.drop_column('users', 'avatar')
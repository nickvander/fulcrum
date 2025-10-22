"""Add user audit log table

Revision ID: 0005_user_audit_log
Revises: 0004_add_user_management_fields_and_address_model
Create Date: 2025-10-20 06:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_user_audit_log'
down_revision: Union[str, None] = '0004_user_mgmt'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_audit_logs table
    op.create_table('user_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action_performed_by', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['action_performed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_audit_logs_id'), 'user_audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_user_audit_logs_action'), 'user_audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_user_audit_logs_user_id'), 'user_audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_audit_logs_action_performed_by'), 'user_audit_logs', ['action_performed_by'], unique=False)


def downgrade() -> None:
    # Drop user_audit_logs table
    op.drop_index(op.f('ix_user_audit_logs_action_performed_by'), table_name='user_audit_logs')
    op.drop_index(op.f('ix_user_audit_logs_user_id'), table_name='user_audit_logs')
    op.drop_index(op.f('ix_user_audit_logs_action'), table_name='user_audit_logs')
    op.drop_index(op.f('ix_user_audit_logs_id'), table_name='user_audit_logs')
    op.drop_table('user_audit_logs')
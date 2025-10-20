"""Add user management fields and address model

Revision ID: 0004_add_user_management_fields_and_address_model
Revises: 0003_add_variant_support
Create Date: 2025-10-19 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_user_mgmt'
down_revision: Union[str, None] = '0003_add_variant_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column('users', sa.Column('employee_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('user_type', sa.String(), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create unique index for employee_id
    op.create_index(op.f('ix_users_employee_id'), 'users', ['employee_id'], unique=True)
    
    # Create addresses table
    op.create_table('addresses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('street', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('postal_code', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('is_billing', sa.Boolean(), nullable=True),
        sa.Column('is_shipping', sa.Boolean(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_addresses_id'), 'addresses', ['id'], unique=False)
    
    # Create password reset tokens table
    op.create_table('password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_reset_tokens_id'), 'password_reset_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop password reset tokens table
    op.drop_table('password_reset_tokens')
    
    # Drop addresses table
    op.drop_table('addresses')
    
    # Remove new columns from users table
    op.drop_index(op.f('ix_users_employee_id'), table_name='users')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'user_type')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'employee_id')
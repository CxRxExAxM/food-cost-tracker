"""Add super admin support

Revision ID: 004
Revises: 003
Create Date: 2024-12-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_super_admin column to users table."""

    # Add is_super_admin column (defaults to 0/False)
    op.add_column('users',
        sa.Column('is_super_admin', sa.Integer(), server_default='0', nullable=False)
    )

    # Create index for quick super admin lookup
    op.create_index('idx_users_super_admin', 'users', ['is_super_admin'])


def downgrade() -> None:
    """Remove super admin support."""

    # Drop index
    op.drop_index('idx_users_super_admin', table_name='users')

    # Drop column
    op.drop_column('users', 'is_super_admin')

"""Add menu_type column to banquet_menus

Revision ID: 017
Revises: 016
Create Date: 2025-02-04

Adds menu_type column to distinguish between banquet and restaurant menus.
Restaurant menus are costed for a single portion (no guest scaling).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add menu_type column with default 'banquet' for existing menus
    op.add_column('banquet_menus',
        sa.Column('menu_type', sa.String(length=20), nullable=False, server_default='banquet')
    )

    # Create index for filtering by menu_type
    op.create_index('idx_banquet_menus_type', 'banquet_menus', ['menu_type'])

    print("Added menu_type column to banquet_menus table")


def downgrade() -> None:
    op.drop_index('idx_banquet_menus_type', 'banquet_menus')
    op.drop_column('banquet_menus', 'menu_type')

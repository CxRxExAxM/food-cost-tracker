"""Add price column to banquet_menu_items

Revision ID: 018
Revises: 017
Create Date: 2025-02-04

Adds price column to menu items for tracking individual item pricing
and calculating item-level food cost percentage.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add price column to menu items
    op.add_column('banquet_menu_items',
        sa.Column('price', sa.Numeric(10, 2), nullable=True)
    )

    print("Added price column to banquet_menu_items table")


def downgrade() -> None:
    op.drop_column('banquet_menu_items', 'price')

"""add choice_count to banquet_menu_items

Revision ID: 015
Revises: 014
Create Date: 2026-01-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '015'
down_revision: Union[str, Sequence[str], None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add choice_count column for 'Choose X' menu items."""
    op.add_column('banquet_menu_items',
        sa.Column('choice_count', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Remove choice_count column."""
    op.drop_column('banquet_menu_items', 'choice_count')

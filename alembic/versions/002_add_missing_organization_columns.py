"""add missing organization columns

Revision ID: 002
Revises: d7d3ba15e17c
Create Date: 2025-12-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, Sequence[str], None] = 'd7d3ba15e17c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to organizations table."""
    # Add missing columns
    op.add_column('organizations', sa.Column('contact_email', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('contact_phone', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('max_distributors', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('organizations', sa.Column('max_ai_parses_per_month', sa.Integer(), nullable=True, server_default='10'))
    op.add_column('organizations', sa.Column('ai_parses_used_this_month', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('organizations', sa.Column('ai_parses_reset_date', sa.DateTime(), nullable=True))
    op.add_column('organizations', sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'))


def downgrade() -> None:
    """Remove the added columns."""
    op.drop_column('organizations', 'is_active')
    op.drop_column('organizations', 'ai_parses_reset_date')
    op.drop_column('organizations', 'ai_parses_used_this_month')
    op.drop_column('organizations', 'max_ai_parses_per_month')
    op.drop_column('organizations', 'max_distributors')
    op.drop_column('organizations', 'contact_phone')
    op.drop_column('organizations', 'contact_email')

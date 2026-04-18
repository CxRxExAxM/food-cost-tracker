"""Add daily_log_token to ehc_outlet for public QR access

Revision ID: 045
Revises: 044
Create Date: 2026-04-17

Enables tokenized public access to daily log workstation,
similar to EHC forms. Each outlet gets a unique token that
allows kitchen staff to access the daily worksheet without
logging in.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '045'
down_revision: Union[str, Sequence[str], None] = '044'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add daily_log_token column to ehc_outlet."""

    # Add token column for public access
    op.add_column('ehc_outlet',
        sa.Column('daily_log_token', sa.String(length=43), nullable=True)
    )

    # Add unique index on token
    op.create_index(
        'idx_ehc_outlet_daily_log_token',
        'ehc_outlet',
        ['daily_log_token'],
        unique=True
    )

    print("Added daily_log_token column to ehc_outlet")


def downgrade() -> None:
    """Remove daily_log_token column."""

    op.drop_index('idx_ehc_outlet_daily_log_token', 'ehc_outlet')
    op.drop_column('ehc_outlet', 'daily_log_token')

    print("Removed daily_log_token column from ehc_outlet")

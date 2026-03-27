"""Add original_filename to EHC submissions

Revision ID: 031
Revises: 030
Create Date: 2026-03-27

Stores the original filename when files are uploaded to submissions,
enabling better UX by showing the actual filename instead of the UUID.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '031'
down_revision: Union[str, Sequence[str], None] = '030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add original_filename column to submissions."""

    op.add_column('ehc_record_submission',
        sa.Column('original_filename', sa.String(length=255), nullable=True)
    )

    print("Added original_filename to ehc_record_submission")


def downgrade() -> None:
    """Remove original_filename from submissions."""

    op.drop_column('ehc_record_submission', 'original_filename')

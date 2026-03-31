"""Add internal_verified to EHC audit points

Revision ID: 032
Revises: 031
Create Date: 2026-03-31

Tracks internal pre-audit walk verification separate from actual audit status.
Allows teams to do practice walks and mark points as internally checked
before the official audit.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '032'
down_revision: Union[str, Sequence[str], None] = '031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add internal_verified column to audit points."""

    op.add_column('ehc_audit_point',
        sa.Column('internal_verified', sa.Boolean(), nullable=False, server_default='false')
    )

    print("Added internal_verified to ehc_audit_point")


def downgrade() -> None:
    """Remove internal_verified from audit points."""

    op.drop_column('ehc_audit_point', 'internal_verified')

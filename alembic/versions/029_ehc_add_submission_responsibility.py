"""Add responsibility_code to EHC submissions

Revision ID: 029
Revises: 028
Create Date: 2026-03-27

Adds responsibility tracking at the submission level (not just record level)
so different people can own different periods/outlets of the same record.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '029'
down_revision: Union[str, Sequence[str], None] = '028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add responsibility_code to submissions."""

    op.add_column('ehc_record_submission',
        sa.Column('responsibility_code', sa.String(length=20), nullable=True)
    )

    # Copy default from parent record where not set
    op.execute("""
        UPDATE ehc_record_submission rs
        SET responsibility_code = r.responsibility_code
        FROM ehc_record r
        WHERE rs.record_id = r.id
        AND rs.responsibility_code IS NULL
    """)

    print("Added responsibility_code to ehc_record_submission")


def downgrade() -> None:
    """Remove responsibility_code from submissions."""

    op.drop_column('ehc_record_submission', 'responsibility_code')

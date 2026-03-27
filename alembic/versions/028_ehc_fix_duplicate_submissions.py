"""Fix duplicate EHC submissions and add unique constraint

Revision ID: 028
Revises: 027
Create Date: 2026-03-27

Fixes:
1. Removes duplicate submissions (keeps the oldest one per unique combination)
2. Adds unique constraint to prevent future duplicates
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '028'
down_revision: Union[str, Sequence[str], None] = '027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove duplicates and add unique constraint."""

    # Step 1: Delete duplicate submissions, keeping the oldest (lowest id)
    # A duplicate is defined as same (audit_cycle_id, record_id, outlet_name, period_label)
    op.execute("""
        DELETE FROM ehc_record_submission
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM ehc_record_submission
            GROUP BY audit_cycle_id, record_id, COALESCE(outlet_name, ''), period_label
        )
    """)

    # Step 2: Add unique constraint to prevent future duplicates
    # Note: outlet_name can be NULL for office_book records, so we use a partial index approach
    # PostgreSQL treats NULLs as distinct in unique constraints, so we use COALESCE
    op.execute("""
        CREATE UNIQUE INDEX idx_ehc_submission_unique
        ON ehc_record_submission (audit_cycle_id, record_id, COALESCE(outlet_name, ''), period_label)
    """)

    print("Cleaned up duplicate submissions and added unique constraint")


def downgrade() -> None:
    """Remove unique constraint (duplicates cannot be restored)."""

    op.execute("DROP INDEX IF EXISTS idx_ehc_submission_unique")

    print("Removed unique constraint (note: deleted duplicates cannot be restored)")

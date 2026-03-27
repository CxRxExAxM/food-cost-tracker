"""Fix duplicate EHC outlet assignments and add unique constraint

Revision ID: 030
Revises: 029
Create Date: 2026-03-27

Fixes duplicate outlet assignments in ehc_record_outlet table.
Same issue as migration 028 fixed for submissions.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '030'
down_revision: Union[str, Sequence[str], None] = '029'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove duplicate outlet assignments and add unique constraint."""

    # Step 1: Delete duplicate outlet assignments, keeping the oldest (lowest id)
    op.execute("""
        DELETE FROM ehc_record_outlet
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM ehc_record_outlet
            GROUP BY record_id, outlet_name
        )
    """)

    # Step 2: Add unique constraint
    op.create_unique_constraint(
        'unique_record_outlet_assignment',
        'ehc_record_outlet',
        ['record_id', 'outlet_name']
    )

    print("Cleaned up duplicate outlet assignments and added unique constraint")


def downgrade() -> None:
    """Remove unique constraint."""

    op.drop_constraint('unique_record_outlet_assignment', 'ehc_record_outlet', type_='unique')

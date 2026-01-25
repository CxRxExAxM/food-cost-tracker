"""add outlet_id to price_history

Revision ID: 012
Revises: 011
Create Date: 2026-01-25

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, Sequence[str], None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add outlet_id column to price_history for multi-outlet pricing."""
    # Add outlet_id column to price_history
    op.add_column('price_history', sa.Column('outlet_id', sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_price_history_outlet',
        'price_history', 'outlets',
        ['outlet_id'], ['id']
    )

    # Add index for outlet_id queries
    op.create_index('idx_price_history_outlet', 'price_history', ['outlet_id'])

    # Backfill outlet_id from import_batches where possible
    op.execute("""
        UPDATE price_history ph
        SET outlet_id = ib.outlet_id
        FROM import_batches ib
        WHERE ph.import_batch_id = ib.batch_id
        AND ph.outlet_id IS NULL
    """)


def downgrade() -> None:
    """Remove outlet_id from price_history."""
    op.drop_index('idx_price_history_outlet', table_name='price_history')
    op.drop_constraint('fk_price_history_outlet', 'price_history', type_='foreignkey')
    op.drop_column('price_history', 'outlet_id')

"""Flexible prep item amounts

Add support for different amount modes (per_person, at_minimum, fixed)
and proper unit references to banquet_prep_items.

Revision ID: 010
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Add unit_id foreign key to units table (replaces free-text amount_unit)
    op.add_column('banquet_prep_items',
        sa.Column('unit_id', sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        'fk_banquet_prep_items_unit',
        'banquet_prep_items', 'units',
        ['unit_id'], ['id'],
        ondelete='SET NULL'
    )

    op.create_index(
        'idx_banquet_prep_items_unit',
        'banquet_prep_items',
        ['unit_id']
    )

    # Add amount_mode column
    # 'per_person' - scales with guest count (default, existing behavior)
    # 'at_minimum' - fixed amount based on menu's min_guest_count
    # 'fixed' - never scales, same amount regardless of guests
    op.add_column('banquet_prep_items',
        sa.Column('amount_mode', sa.String(length=20), nullable=True, server_default='per_person')
    )

    # Add check constraint for valid amount modes
    op.create_check_constraint(
        'check_valid_amount_mode',
        'banquet_prep_items',
        "amount_mode IN ('per_person', 'at_minimum', 'fixed')"
    )

    # Add base_amount column for at_minimum/fixed modes
    # For 'per_person', amount_per_guest is used
    # For 'at_minimum' and 'fixed', base_amount is used
    op.add_column('banquet_prep_items',
        sa.Column('base_amount', sa.Numeric(precision=10, scale=4), nullable=True)
    )

    print("✅ Added unit_id, amount_mode, and base_amount to banquet_prep_items")


def downgrade():
    # Remove check constraint
    op.drop_constraint('check_valid_amount_mode', 'banquet_prep_items', type_='check')

    # Remove base_amount column
    op.drop_column('banquet_prep_items', 'base_amount')

    # Remove amount_mode column
    op.drop_column('banquet_prep_items', 'amount_mode')

    # Remove unit_id index
    op.drop_index('idx_banquet_prep_items_unit', 'banquet_prep_items')

    # Remove unit_id foreign key
    op.drop_constraint('fk_banquet_prep_items_unit', 'banquet_prep_items', type_='foreignkey')

    # Remove unit_id column
    op.drop_column('banquet_prep_items', 'unit_id')

    print("✅ Removed flexible prep amount columns from banquet_prep_items")

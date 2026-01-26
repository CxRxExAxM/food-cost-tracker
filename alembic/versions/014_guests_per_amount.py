"""Add guests_per_amount for flexible scaling

Replace amount_mode with guests_per_amount for simpler "per X guests" calculation.
- guests_per_amount = 1 means "per person" (same as old per_person mode)
- guests_per_amount = 10 means "per 10 guests" (e.g., 1 bottle per 10 guests)

Calculation: total = (guest_count / guests_per_amount) * amount_per_guest

Revision ID: 014
Revises: 013
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    # Add guests_per_amount column (default 1 = per person)
    op.add_column('banquet_prep_items',
        sa.Column('guests_per_amount', sa.Integer(), nullable=True, server_default='1')
    )

    # Migrate existing data:
    # - per_person: guests_per_amount = 1 (default, no change needed)
    # - at_minimum/fixed: Convert base_amount to amount_per_guest with guests_per_amount = 1
    #   (effectively treating them as fixed amounts for 1 guest batch)
    op.execute("""
        UPDATE banquet_prep_items
        SET amount_per_guest = base_amount,
            guests_per_amount = 1
        WHERE amount_mode IN ('at_minimum', 'fixed')
          AND base_amount IS NOT NULL
          AND (amount_per_guest IS NULL OR amount_per_guest = 0)
    """)

    # Drop the old check constraint so we don't have to maintain it
    try:
        op.drop_constraint('check_valid_amount_mode', 'banquet_prep_items', type_='check')
    except:
        # Constraint might not exist in all environments
        pass

    print("✅ Added guests_per_amount to banquet_prep_items")


def downgrade():
    # Remove guests_per_amount column
    op.drop_column('banquet_prep_items', 'guests_per_amount')

    # Recreate check constraint
    op.create_check_constraint(
        'check_valid_amount_mode',
        'banquet_prep_items',
        "amount_mode IN ('per_person', 'at_minimum', 'fixed')"
    )

    print("✅ Removed guests_per_amount from banquet_prep_items")

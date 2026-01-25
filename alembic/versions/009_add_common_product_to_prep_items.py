"""Add common_product_id to banquet_prep_items

This migration adds common_product_id to banquet_prep_items table,
similar to how recipe_ingredients links to common products.
This allows prep items to link to common products for costing.

Revision ID: 009
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Add common_product_id column to banquet_prep_items
    op.add_column('banquet_prep_items',
        sa.Column('common_product_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_banquet_prep_items_common_product',
        'banquet_prep_items', 'common_products',
        ['common_product_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add index for common_product_id
    op.create_index(
        'idx_banquet_prep_items_common_product',
        'banquet_prep_items',
        ['common_product_id']
    )

    # Update the check constraint to allow common_product_id as an option
    # First drop the old constraint
    op.drop_constraint('check_single_link', 'banquet_prep_items', type_='check')

    # Create new constraint that allows product_id OR recipe_id OR common_product_id
    op.create_check_constraint(
        'check_single_link',
        'banquet_prep_items',
        """(
            (product_id IS NULL AND recipe_id IS NULL AND common_product_id IS NULL) OR
            (product_id IS NOT NULL AND recipe_id IS NULL AND common_product_id IS NULL) OR
            (product_id IS NULL AND recipe_id IS NOT NULL AND common_product_id IS NULL) OR
            (product_id IS NULL AND recipe_id IS NULL AND common_product_id IS NOT NULL)
        )"""
    )


def downgrade():
    # Drop the new constraint
    op.drop_constraint('check_single_link', 'banquet_prep_items', type_='check')

    # Restore original constraint
    op.create_check_constraint(
        'check_single_link',
        'banquet_prep_items',
        """(
            (product_id IS NULL AND recipe_id IS NULL) OR
            (product_id IS NOT NULL AND recipe_id IS NULL) OR
            (product_id IS NULL AND recipe_id IS NOT NULL)
        )"""
    )

    # Drop index
    op.drop_index('idx_banquet_prep_items_common_product', 'banquet_prep_items')

    # Drop foreign key
    op.drop_constraint('fk_banquet_prep_items_common_product', 'banquet_prep_items', type_='foreignkey')

    # Drop column
    op.drop_column('banquet_prep_items', 'common_product_id')

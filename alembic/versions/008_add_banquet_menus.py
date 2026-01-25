"""add banquet menus support

Revision ID: 008
Revises: 007
Create Date: 2025-01-21

Banquet menu support implementation:
- Creates banquet_menus table for menu containers
- Creates banquet_menu_items table for items within menus
- Creates banquet_prep_items table for prep items within menu items
- Supports linking prep items to products OR recipes
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, Sequence[str], None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add banquet menus infrastructure."""

    # ============================================
    # Table 1: banquet_menus
    # The main menu container
    # ============================================
    op.create_table('banquet_menus',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('outlet_id', sa.Integer(), nullable=False),

        # Hierarchy identifiers
        sa.Column('meal_period', sa.String(length=50), nullable=False),
        sa.Column('service_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),

        # Pricing
        sa.Column('price_per_person', sa.Numeric(10, 2), nullable=True),

        # Guest thresholds
        sa.Column('min_guest_count', sa.Integer(), nullable=True),
        sa.Column('under_min_surcharge', sa.Numeric(10, 2), nullable=True),

        # Food cost targets
        sa.Column('target_food_cost_pct', sa.Numeric(5, 2), nullable=True),

        # Metadata
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_banquet_menus_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outlet_id'], ['outlets.id'], name='fk_banquet_menus_outlet', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('outlet_id', 'meal_period', 'service_type', 'name', name='unique_menu_per_outlet')
    )

    # Indexes for banquet_menus
    op.create_index('idx_banquet_menus_org', 'banquet_menus', ['organization_id'])
    op.create_index('idx_banquet_menus_outlet', 'banquet_menus', ['outlet_id'])
    op.create_index('idx_banquet_menus_meal_period', 'banquet_menus', ['meal_period'])
    op.create_index('idx_banquet_menus_service_type', 'banquet_menus', ['service_type'])

    # ============================================
    # Table 2: banquet_menu_items
    # Items within a menu (Oatmeal, Omelets, etc.)
    # ============================================
    op.create_table('banquet_menu_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('banquet_menu_id', sa.Integer(), nullable=False),

        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'),

        # Enhancement/upsell pricing
        sa.Column('is_enhancement', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('additional_price', sa.Numeric(10, 2), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['banquet_menu_id'], ['banquet_menus.id'], name='fk_banquet_menu_items_menu', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for banquet_menu_items
    op.create_index('idx_banquet_menu_items_menu', 'banquet_menu_items', ['banquet_menu_id'])

    # ============================================
    # Table 3: banquet_prep_items
    # Prep items within a menu item (ingredients/components)
    # ============================================
    op.create_table('banquet_prep_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('banquet_menu_item_id', sa.Integer(), nullable=False),

        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'),

        # Amount per guest
        sa.Column('amount_per_guest', sa.Numeric(10, 4), nullable=True),
        sa.Column('amount_unit', sa.String(length=20), nullable=True),

        # Optional categorization (future lookup tables)
        sa.Column('vessel', sa.String(length=100), nullable=True),
        sa.Column('responsibility', sa.String(length=100), nullable=True),

        # Link to product OR recipe (one or the other, not both)
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('recipe_id', sa.Integer(), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['banquet_menu_item_id'], ['banquet_menu_items.id'], name='fk_banquet_prep_items_menu_item', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_banquet_prep_items_product', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], name='fk_banquet_prep_items_recipe', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        # Ensure only one link type (product OR recipe, not both)
        sa.CheckConstraint(
            '(product_id IS NULL AND recipe_id IS NULL) OR '
            '(product_id IS NOT NULL AND recipe_id IS NULL) OR '
            '(product_id IS NULL AND recipe_id IS NOT NULL)',
            name='check_single_link'
        )
    )

    # Indexes for banquet_prep_items
    op.create_index('idx_banquet_prep_items_menu_item', 'banquet_prep_items', ['banquet_menu_item_id'])
    op.create_index('idx_banquet_prep_items_product', 'banquet_prep_items', ['product_id'])
    op.create_index('idx_banquet_prep_items_recipe', 'banquet_prep_items', ['recipe_id'])

    print("✅ Banquet menus infrastructure created")


def downgrade() -> None:
    """Remove banquet menus infrastructure."""

    # Drop indexes and tables in reverse order
    op.drop_index('idx_banquet_prep_items_recipe', 'banquet_prep_items')
    op.drop_index('idx_banquet_prep_items_product', 'banquet_prep_items')
    op.drop_index('idx_banquet_prep_items_menu_item', 'banquet_prep_items')
    op.drop_table('banquet_prep_items')

    op.drop_index('idx_banquet_menu_items_menu', 'banquet_menu_items')
    op.drop_table('banquet_menu_items')

    op.drop_index('idx_banquet_menus_service_type', 'banquet_menus')
    op.drop_index('idx_banquet_menus_meal_period', 'banquet_menus')
    op.drop_index('idx_banquet_menus_outlet', 'banquet_menus')
    op.drop_index('idx_banquet_menus_org', 'banquet_menus')
    op.drop_table('banquet_menus')

    print("✅ Banquet menus infrastructure removed")

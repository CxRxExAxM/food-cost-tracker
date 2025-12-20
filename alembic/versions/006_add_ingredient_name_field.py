"""add ingredient_name field for optional product mapping

Revision ID: 006
Revises: 005
Create Date: 2025-12-18

Adds support for text-only ingredients without product mapping:
- ingredient_name column to recipe_ingredients table
- Allows progressive enhancement: add ingredients as text, map products later
- Backfills existing records with product names for consistency
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, Sequence[str], None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ============================================
    # Step 1: Add ingredient_name column
    # ============================================
    op.add_column(
        'recipe_ingredients',
        sa.Column('ingredient_name', sa.String(255), nullable=True)
    )

    print("✅ Added ingredient_name column to recipe_ingredients")

    # ============================================
    # Step 2: Backfill existing records
    # ============================================
    # For existing records that have common_product_id, copy the product name
    # This ensures historical data displays correctly
    op.execute("""
        UPDATE recipe_ingredients ri
        SET ingredient_name = cp.common_name
        FROM common_products cp
        WHERE ri.common_product_id = cp.id
        AND ri.ingredient_name IS NULL
    """)

    print("✅ Backfilled ingredient_name from common_products")

    # For records with sub_recipe_id, copy the recipe name
    op.execute("""
        UPDATE recipe_ingredients ri
        SET ingredient_name = r.name
        FROM recipes r
        WHERE ri.sub_recipe_id = r.id
        AND ri.ingredient_name IS NULL
    """)

    print("✅ Backfilled ingredient_name from sub-recipes")
    print("✅ Optional product mapping support added")


def downgrade() -> None:
    """Downgrade schema."""

    # Remove ingredient_name column
    op.drop_column('recipe_ingredients', 'ingredient_name')

    print("✅ Removed ingredient_name column from recipe_ingredients")

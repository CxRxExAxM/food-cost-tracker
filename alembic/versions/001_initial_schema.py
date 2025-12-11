"""initial_schema

Revision ID: 001
Revises:
Create Date: 2025-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint("role IN ('admin', 'chef', 'viewer')", name='check_role'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Create distributors table
    op.create_table('distributors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('contact_info', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )

    # Create units table
    op.create_table('units',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('abbreviation', sa.String(), nullable=False),
        sa.Column('unit_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('abbreviation')
    )

    # Create common_products table
    op.create_table('common_products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('common_name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('subcategory', sa.String(), nullable=True),
        sa.Column('preferred_unit_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('allergen_vegan', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_vegetarian', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_gluten', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_crustation', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_egg', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_mollusk', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_fish', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_lupin', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_dairy', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_tree_nuts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_peanuts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_sesame', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_soy', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_sulphur_dioxide', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_mustard', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('allergen_celery', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['preferred_unit_id'], ['units.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('common_name')
    )

    # Create products table
    op.create_table('products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('brand', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('pack', sa.Integer(), nullable=True),
        sa.Column('size', sa.Float(), nullable=True),
        sa.Column('unit_id', sa.Integer(), nullable=True),
        sa.Column('common_product_id', sa.Integer(), nullable=True),
        sa.Column('is_catch_weight', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
        sa.ForeignKeyConstraint(['common_product_id'], ['common_products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create recipes table
    op.create_table('recipes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('category_path', sa.String(), nullable=True),
        sa.Column('yield_amount', sa.Float(), nullable=True),
        sa.Column('yield_unit_id', sa.Integer(), nullable=True),
        sa.Column('servings', sa.Float(), nullable=True),
        sa.Column('serving_unit_id', sa.Integer(), nullable=True),
        sa.Column('prep_time_minutes', sa.Integer(), nullable=True),
        sa.Column('cook_time_minutes', sa.Integer(), nullable=True),
        sa.Column('method', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['yield_unit_id'], ['units.id'], ),
        sa.ForeignKeyConstraint(['serving_unit_id'], ['units.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create distributor_products table
    op.create_table('distributor_products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('distributor_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('distributor_sku', sa.String(), nullable=False),
        sa.Column('distributor_name', sa.String(), nullable=True),
        sa.Column('is_available', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['distributor_id'], ['distributors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('distributor_id', 'distributor_sku', name='unique_distributor_sku')
    )

    # Create import_batches table
    op.create_table('import_batches',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('distributor_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('rows_imported', sa.Integer(), nullable=True),
        sa.Column('rows_failed', sa.Integer(), nullable=True),
        sa.Column('import_date', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['distributor_id'], ['distributors.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create recipe_ingredients table
    op.create_table('recipe_ingredients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('common_product_id', sa.Integer(), nullable=True),
        sa.Column('sub_recipe_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=True),
        sa.Column('yield_percentage', sa.Float(), nullable=True, server_default='100.00'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['common_product_id'], ['common_products.id'], ),
        sa.ForeignKeyConstraint(['sub_recipe_id'], ['recipes.id'], ),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create price_history table
    op.create_table('price_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('distributor_product_id', sa.Integer(), nullable=False),
        sa.Column('case_price', sa.Float(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=True),
        sa.Column('effective_date', sa.DateTime(), nullable=False),
        sa.Column('import_batch_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['distributor_product_id'], ['distributor_products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('distributor_product_id', 'effective_date', name='unique_price_per_date')
    )

    # Create indexes
    op.create_index('idx_products_common_product', 'products', ['common_product_id'])
    op.create_index('idx_common_products_name', 'common_products', ['common_name'])
    op.create_index('idx_distributor_products_distributor', 'distributor_products', ['distributor_id'])
    op.create_index('idx_distributor_products_product', 'distributor_products', ['product_id'])
    op.create_index('idx_distributor_products_sku', 'distributor_products', ['distributor_sku'])
    op.create_index('idx_price_history_dist_prod', 'price_history', ['distributor_product_id'])
    op.create_index('idx_price_history_date', 'price_history', [sa.text('effective_date DESC')])
    op.create_index('idx_recipe_ingredients_recipe', 'recipe_ingredients', ['recipe_id'])
    op.create_index('idx_recipe_ingredients_common_product', 'recipe_ingredients', ['common_product_id'])

    # Seed default distributors
    op.execute("""
        INSERT INTO distributors (name, code) VALUES
        ('Sysco', 'sysco'),
        ('Vesta', 'vesta'),
        ('SM Seafood', 'smseafood'),
        ('Shamrock', 'shamrock'),
        ('Noble Bread', 'noblebread'),
        ('Sterling', 'sterling')
    """)

    # Seed default units
    op.execute("""
        INSERT INTO units (name, abbreviation, unit_type) VALUES
        ('Pound', 'LB', 'weight'),
        ('Ounce', 'OZ', 'weight'),
        ('Kilogram', 'KG', 'weight'),
        ('Gram', 'G', 'weight'),
        ('Gallon', 'GAL', 'volume'),
        ('Quart', 'QT', 'volume'),
        ('Pint', 'PT', 'volume'),
        ('Cup', 'CUP', 'volume'),
        ('Fluid Ounce', 'FL OZ', 'volume'),
        ('Liter', 'L', 'volume'),
        ('Milliliter', 'ML', 'volume'),
        ('Tablespoon', 'TBSP', 'volume'),
        ('Teaspoon', 'TSP', 'volume'),
        ('Each', 'EA', 'count'),
        ('Count', 'CT', 'count'),
        ('Dozen', 'DOZ', 'count'),
        ('Case', 'CASE', 'count'),
        ('Box', 'BOX', 'count'),
        ('Bag', 'BAG', 'count'),
        ('Can', 'CAN', 'count'),
        ('Jar', 'JAR', 'count'),
        ('Pack', 'PACK', 'count'),
        ('Bunch', 'BUNCH', 'count')
    """)


def downgrade() -> None:
    op.drop_index('idx_recipe_ingredients_common_product', table_name='recipe_ingredients')
    op.drop_index('idx_recipe_ingredients_recipe', table_name='recipe_ingredients')
    op.drop_index('idx_price_history_date', table_name='price_history')
    op.drop_index('idx_price_history_dist_prod', table_name='price_history')
    op.drop_index('idx_distributor_products_sku', table_name='distributor_products')
    op.drop_index('idx_distributor_products_product', table_name='distributor_products')
    op.drop_index('idx_distributor_products_distributor', table_name='distributor_products')
    op.drop_index('idx_common_products_name', table_name='common_products')
    op.drop_index('idx_products_common_product', table_name='products')
    op.drop_table('price_history')
    op.drop_table('recipe_ingredients')
    op.drop_table('import_batches')
    op.drop_table('distributor_products')
    op.drop_table('recipes')
    op.drop_table('products')
    op.drop_table('common_products')
    op.drop_table('units')
    op.drop_table('distributors')
    op.drop_table('users')

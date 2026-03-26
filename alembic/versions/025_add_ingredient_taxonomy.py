"""Add ingredient taxonomy tables (base_ingredients, ingredient_variants)

Revision ID: 025
Revises: 024
Create Date: 2026-03-26

Implements attribute-based ingredient taxonomy for:
- Consistent cross-vendor ingredient identification
- Attribute-based filtering and cost rollups
- Foundation for AI invoice and recipe parsing improvements

See docs/INGREDIENT_TAXONOMY_DESIGN.md for full design context.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. Create base_ingredients table
    # ==========================================================================
    op.create_table(
        'base_ingredients',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50)),       # "Produce", "Protein", "Dairy"
        sa.Column('subcategory', sa.String(50)),    # "Vegetables", "Poultry", "Cheese"
        sa.Column('default_unit_id', sa.Integer(), sa.ForeignKey('units.id', ondelete='SET NULL')),

        # Allergen flags (inherited by variants unless overridden)
        # Match existing common_products pattern: Integer with 0/1
        sa.Column('allergen_vegan', sa.Integer(), server_default='0'),
        sa.Column('allergen_vegetarian', sa.Integer(), server_default='0'),
        sa.Column('allergen_gluten', sa.Integer(), server_default='0'),
        sa.Column('allergen_crustation', sa.Integer(), server_default='0'),
        sa.Column('allergen_egg', sa.Integer(), server_default='0'),
        sa.Column('allergen_mollusk', sa.Integer(), server_default='0'),
        sa.Column('allergen_fish', sa.Integer(), server_default='0'),
        sa.Column('allergen_lupin', sa.Integer(), server_default='0'),
        sa.Column('allergen_dairy', sa.Integer(), server_default='0'),
        sa.Column('allergen_tree_nuts', sa.Integer(), server_default='0'),
        sa.Column('allergen_peanuts', sa.Integer(), server_default='0'),
        sa.Column('allergen_sesame', sa.Integer(), server_default='0'),
        sa.Column('allergen_soy', sa.Integer(), server_default='0'),
        sa.Column('allergen_sulphur_dioxide', sa.Integer(), server_default='0'),
        sa.Column('allergen_mustard', sa.Integer(), server_default='0'),
        sa.Column('allergen_celery', sa.Integer(), server_default='0'),

        sa.Column('is_active', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Unique constraint on name (base ingredients are global)
    op.create_unique_constraint('uq_base_ingredients_name', 'base_ingredients', ['name'])

    # Index for category browsing
    op.create_index('idx_base_ingredients_category', 'base_ingredients', ['category'])

    # ==========================================================================
    # 2. Create ingredient_variants table
    # ==========================================================================
    op.create_table(
        'ingredient_variants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('base_ingredient_id', sa.Integer(),
                  sa.ForeignKey('base_ingredients.id', ondelete='CASCADE'), nullable=False),

        # General attributes (produce, all categories)
        sa.Column('variety', sa.String(50)),        # "Orange", "Rainbow", "Roma"
        sa.Column('form', sa.String(50)),           # "Baby", "Jumbo", "Petite"
        sa.Column('prep', sa.String(50)),           # "Diced", "Peeled", "Sliced"
        sa.Column('cut_size', sa.String(30)),       # "1/2 inch", "1/4 inch"

        # Protein-specific attributes
        sa.Column('cut', sa.String(50)),            # "Breast", "Thigh", "Loin"
        sa.Column('bone', sa.String(30)),           # "Boneless", "Bone-In"
        sa.Column('skin', sa.String(30)),           # "Skin On", "Skinless"
        sa.Column('grade', sa.String(30)),          # "Natural", "Choice", "Prime"
        sa.Column('state', sa.String(30)),          # "Fresh", "Frozen", "IQF"

        # Display name (computed or user-set)
        sa.Column('display_name', sa.String(255), nullable=False),

        # Override allergens if different from base (JSON: {"allergen_gluten": 1})
        sa.Column('allergen_override', sa.JSON()),

        sa.Column('is_active', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Index for fast lookup by base ingredient
    op.create_index('idx_variants_base', 'ingredient_variants', ['base_ingredient_id'])

    # Partial indexes for attribute filtering (only index non-null values)
    op.execute('''
        CREATE INDEX idx_variants_variety ON ingredient_variants(variety)
        WHERE variety IS NOT NULL
    ''')
    op.execute('''
        CREATE INDEX idx_variants_form ON ingredient_variants(form)
        WHERE form IS NOT NULL
    ''')
    op.execute('''
        CREATE INDEX idx_variants_prep ON ingredient_variants(prep)
        WHERE prep IS NOT NULL
    ''')
    op.execute('''
        CREATE INDEX idx_variants_state ON ingredient_variants(state)
        WHERE state IS NOT NULL
    ''')

    # Unique constraint on attribute combination (prevents duplicates)
    # Note: NULL values are treated as distinct in PostgreSQL unique constraints
    # This is intentional - allows multiple variants with some null attributes
    op.create_unique_constraint(
        'uq_variant_attributes',
        'ingredient_variants',
        ['base_ingredient_id', 'variety', 'form', 'prep', 'cut_size',
         'cut', 'bone', 'skin', 'grade', 'state']
    )

    # ==========================================================================
    # 3. Add bridge columns to common_products (non-breaking)
    # ==========================================================================
    op.add_column('common_products',
        sa.Column('base_ingredient_id', sa.Integer(),
                  sa.ForeignKey('base_ingredients.id', ondelete='SET NULL')))
    op.add_column('common_products',
        sa.Column('variant_id', sa.Integer(),
                  sa.ForeignKey('ingredient_variants.id', ondelete='SET NULL')))
    op.add_column('common_products',
        sa.Column('migrated_at', sa.DateTime()))

    op.create_index('idx_common_products_base', 'common_products', ['base_ingredient_id'])
    op.create_index('idx_common_products_variant', 'common_products', ['variant_id'])

    # ==========================================================================
    # 4. Add taxonomy columns to ingredient_mappings (for learning loop)
    # ==========================================================================
    op.add_column('ingredient_mappings',
        sa.Column('base_ingredient_id', sa.Integer(),
                  sa.ForeignKey('base_ingredients.id', ondelete='SET NULL')))
    op.add_column('ingredient_mappings',
        sa.Column('variant_id', sa.Integer(),
                  sa.ForeignKey('ingredient_variants.id', ondelete='SET NULL')))
    op.add_column('ingredient_mappings',
        sa.Column('source_type', sa.String(20), server_default='recipe'))  # 'recipe' or 'invoice'
    op.add_column('ingredient_mappings',
        sa.Column('vendor_code', sa.String(20)))  # Distributor identifier for invoice mappings

    # Index for invoice lookup (vendor_code + raw_name)
    op.execute('''
        CREATE INDEX idx_ingredient_mappings_invoice
        ON ingredient_mappings(organization_id, vendor_code, LOWER(raw_name))
        WHERE source_type = 'invoice'
    ''')


def downgrade():
    # Remove ingredient_mappings additions
    op.execute('DROP INDEX IF EXISTS idx_ingredient_mappings_invoice')
    op.drop_column('ingredient_mappings', 'vendor_code')
    op.drop_column('ingredient_mappings', 'source_type')
    op.drop_column('ingredient_mappings', 'variant_id')
    op.drop_column('ingredient_mappings', 'base_ingredient_id')

    # Remove common_products bridge columns
    op.drop_index('idx_common_products_variant', table_name='common_products')
    op.drop_index('idx_common_products_base', table_name='common_products')
    op.drop_column('common_products', 'migrated_at')
    op.drop_column('common_products', 'variant_id')
    op.drop_column('common_products', 'base_ingredient_id')

    # Drop ingredient_variants
    op.drop_constraint('uq_variant_attributes', 'ingredient_variants', type_='unique')
    op.execute('DROP INDEX IF EXISTS idx_variants_state')
    op.execute('DROP INDEX IF EXISTS idx_variants_prep')
    op.execute('DROP INDEX IF EXISTS idx_variants_form')
    op.execute('DROP INDEX IF EXISTS idx_variants_variety')
    op.drop_index('idx_variants_base', table_name='ingredient_variants')
    op.drop_table('ingredient_variants')

    # Drop base_ingredients
    op.drop_index('idx_base_ingredients_category', table_name='base_ingredients')
    op.drop_constraint('uq_base_ingredients_name', 'base_ingredients', type_='unique')
    op.drop_table('base_ingredients')

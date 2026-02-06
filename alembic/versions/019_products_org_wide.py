"""products org-wide migration

Revision ID: 019
Revises: 018
Create Date: 2026-02-06

Phase 7: Migrate products from outlet-specific to organization-wide.
- Products become org-wide (outlet_id removed from products and distributor_products)
- Price history retains outlet_id for outlet-specific pricing
- Duplicate products are merged (same name/brand/pack/size/unit within org)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '019'
down_revision: Union[str, Sequence[str], None] = '018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make products organization-wide instead of outlet-specific."""

    # ============================================
    # Step 1: Create migration log table for rollback tracking
    # ============================================
    op.create_table('product_migration_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('merged_product_id', sa.Integer(), nullable=False),
        sa.Column('kept_product_id', sa.Integer(), nullable=False),
        sa.Column('original_outlet_id', sa.Integer(), nullable=True),
        sa.Column('migration_date', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_migration_log_merged', 'product_migration_log', ['merged_product_id'])
    op.create_index('idx_migration_log_kept', 'product_migration_log', ['kept_product_id'])

    # ============================================
    # Step 2: Identify and merge duplicate products
    # ============================================
    # For each set of duplicates (same name/brand/pack/size/unit_id/org_id),
    # keep the lowest ID and remap all distributor_products to it

    op.execute("""
        -- Create a temp table with duplicate groups
        CREATE TEMP TABLE duplicate_groups AS
        SELECT
            organization_id,
            name,
            COALESCE(brand, '') as brand,
            COALESCE(pack, 0) as pack,
            COALESCE(size, 0) as size,
            COALESCE(unit_id, 0) as unit_id,
            MIN(id) as keep_id,
            ARRAY_AGG(id ORDER BY id) as all_ids
        FROM products
        WHERE is_active = 1
        GROUP BY organization_id, name, COALESCE(brand, ''), COALESCE(pack, 0),
                 COALESCE(size, 0), COALESCE(unit_id, 0)
        HAVING COUNT(*) > 1
    """)

    # Log all merges for potential rollback
    op.execute("""
        INSERT INTO product_migration_log (merged_product_id, kept_product_id, original_outlet_id)
        SELECT
            p.id as merged_product_id,
            dg.keep_id as kept_product_id,
            p.outlet_id as original_outlet_id
        FROM products p
        JOIN duplicate_groups dg ON
            p.organization_id = dg.organization_id
            AND p.name = dg.name
            AND COALESCE(p.brand, '') = dg.brand
            AND COALESCE(p.pack, 0) = dg.pack
            AND COALESCE(p.size, 0) = dg.size
            AND COALESCE(p.unit_id, 0) = dg.unit_id
        WHERE p.id != dg.keep_id
    """)

    # Remap distributor_products from merged products to kept products
    op.execute("""
        UPDATE distributor_products dp
        SET product_id = ml.kept_product_id
        FROM product_migration_log ml
        WHERE dp.product_id = ml.merged_product_id
    """)

    # Soft-delete merged products
    op.execute("""
        UPDATE products
        SET is_active = 0
        FROM product_migration_log ml
        WHERE products.id = ml.merged_product_id
    """)

    # Clean up temp table
    op.execute("DROP TABLE duplicate_groups")

    # ============================================
    # Step 3: Drop outlet_id from products table
    # ============================================
    op.drop_index('idx_products_outlet', table_name='products')
    op.drop_constraint('fk_products_outlet', 'products', type_='foreignkey')
    op.drop_column('products', 'outlet_id')

    # ============================================
    # Step 4: Drop outlet_id from distributor_products table
    # ============================================
    op.drop_index('idx_distributor_products_outlet', table_name='distributor_products')
    op.drop_constraint('fk_distributor_products_outlet', 'distributor_products', type_='foreignkey')
    op.drop_column('distributor_products', 'outlet_id')

    # Note: price_history.outlet_id is KEPT for outlet-specific pricing

    print("✅ Products migrated to org-wide. outlet_id removed from products and distributor_products.")
    print("   Price history retains outlet_id for outlet-specific pricing.")


def downgrade() -> None:
    """Restore outlet-specific products."""

    # ============================================
    # Step 1: Re-add outlet_id to products table
    # ============================================
    op.add_column('products', sa.Column('outlet_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_products_outlet', 'products', 'outlets', ['outlet_id'], ['id'])
    op.create_index('idx_products_outlet', 'products', ['outlet_id'])

    # ============================================
    # Step 2: Re-add outlet_id to distributor_products table
    # ============================================
    op.add_column('distributor_products', sa.Column('outlet_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_distributor_products_outlet', 'distributor_products', 'outlets', ['outlet_id'], ['id'])
    op.create_index('idx_distributor_products_outlet', 'distributor_products', ['outlet_id'])

    # ============================================
    # Step 3: Restore outlet_id from default outlet
    # ============================================
    # Assign products to their organization's default outlet
    op.execute("""
        UPDATE products p
        SET outlet_id = (
            SELECT o.id
            FROM outlets o
            WHERE o.organization_id = p.organization_id
            ORDER BY o.id
            LIMIT 1
        )
    """)

    op.execute("""
        UPDATE distributor_products dp
        SET outlet_id = (
            SELECT o.id
            FROM outlets o
            WHERE o.organization_id = dp.organization_id
            ORDER BY o.id
            LIMIT 1
        )
    """)

    # ============================================
    # Step 4: Re-activate merged products (if migration log exists)
    # ============================================
    op.execute("""
        UPDATE products p
        SET is_active = 1,
            outlet_id = ml.original_outlet_id
        FROM product_migration_log ml
        WHERE p.id = ml.merged_product_id
    """)

    # Remap distributor_products back to their original products
    op.execute("""
        UPDATE distributor_products dp
        SET product_id = ml.merged_product_id
        FROM product_migration_log ml
        WHERE dp.product_id = ml.kept_product_id
          AND EXISTS (
              SELECT 1 FROM products p
              WHERE p.id = ml.merged_product_id
              AND p.is_active = 1
          )
    """)

    # ============================================
    # Step 5: Drop migration log table
    # ============================================
    op.drop_index('idx_migration_log_kept', table_name='product_migration_log')
    op.drop_index('idx_migration_log_merged', table_name='product_migration_log')
    op.drop_table('product_migration_log')

    print("✅ Products restored to outlet-specific. outlet_id re-added to products and distributor_products.")

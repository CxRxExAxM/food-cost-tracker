"""add outlets support

Revision ID: 003
Revises: 002
Create Date: 2025-12-12

Multi-outlet support implementation:
- Creates outlets table for outlet management
- Creates user_outlets junction table for many-to-many user-outlet relationships
- Adds outlet_id to products, recipes, distributor_products, import_batches
- Migrates existing organizations to use "Default Outlet"
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, Sequence[str], None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add outlets infrastructure and migrate existing data."""

    # ============================================
    # Step 1: Create outlets table
    # ============================================
    op.create_table('outlets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_outlets_organization'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_outlets_organization', 'outlets', ['organization_id'])

    # ============================================
    # Step 2: Create user_outlets junction table
    # ============================================
    op.create_table('user_outlets',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('outlet_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_outlets_user', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outlet_id'], ['outlets.id'], name='fk_user_outlets_outlet', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'outlet_id')
    )
    op.create_index('idx_user_outlets_user', 'user_outlets', ['user_id'])
    op.create_index('idx_user_outlets_outlet', 'user_outlets', ['outlet_id'])

    # ============================================
    # Step 3: Add outlet_id to existing tables
    # ============================================

    # Products - outlet-specific
    op.add_column('products', sa.Column('outlet_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_products_outlet', 'products', 'outlets', ['outlet_id'], ['id'])
    op.create_index('idx_products_outlet', 'products', ['outlet_id'])

    # Recipes - outlet-specific
    op.add_column('recipes', sa.Column('outlet_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_recipes_outlet', 'recipes', 'outlets', ['outlet_id'], ['id'])
    op.create_index('idx_recipes_outlet', 'recipes', ['outlet_id'])

    # Distributor Products - outlet-specific
    op.add_column('distributor_products', sa.Column('outlet_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_distributor_products_outlet', 'distributor_products', 'outlets', ['outlet_id'], ['id'])
    op.create_index('idx_distributor_products_outlet', 'distributor_products', ['outlet_id'])

    # Import Batches - outlet-specific
    op.add_column('import_batches', sa.Column('outlet_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_import_batches_outlet', 'import_batches', 'outlets', ['outlet_id'], ['id'])
    op.create_index('idx_import_batches_outlet', 'import_batches', ['outlet_id'])

    # ============================================
    # Step 4: Data Migration - Create Default Outlets
    # ============================================
    # This uses raw SQL to create a "Default Outlet" for each existing organization
    # and assign all existing data to that outlet

    # Note: Using PostgreSQL-specific syntax
    op.execute("""
        -- Create "Default Outlet" for each organization
        INSERT INTO outlets (organization_id, name, location, is_active)
        SELECT id, 'Default Outlet', NULL, 1
        FROM organizations
        WHERE is_active = 1;
    """)

    op.execute("""
        -- Update products to use their organization's default outlet
        UPDATE products p
        SET outlet_id = (
            SELECT o.id
            FROM outlets o
            WHERE o.organization_id = p.organization_id
            AND o.name = 'Default Outlet'
            LIMIT 1
        )
        WHERE p.outlet_id IS NULL;
    """)

    op.execute("""
        -- Update recipes to use their organization's default outlet
        UPDATE recipes r
        SET outlet_id = (
            SELECT o.id
            FROM outlets o
            WHERE o.organization_id = r.organization_id
            AND o.name = 'Default Outlet'
            LIMIT 1
        )
        WHERE r.outlet_id IS NULL;
    """)

    op.execute("""
        -- Update distributor_products to use their organization's default outlet
        UPDATE distributor_products dp
        SET outlet_id = (
            SELECT o.id
            FROM outlets o
            WHERE o.organization_id = dp.organization_id
            AND o.name = 'Default Outlet'
            LIMIT 1
        )
        WHERE dp.outlet_id IS NULL;
    """)

    op.execute("""
        -- Update import_batches to use their organization's default outlet
        UPDATE import_batches ib
        SET outlet_id = (
            SELECT o.id
            FROM outlets o
            WHERE o.organization_id = ib.organization_id
            AND o.name = 'Default Outlet'
            LIMIT 1
        )
        WHERE ib.outlet_id IS NULL;
    """)

    print("✅ Outlets infrastructure created and existing data migrated to Default Outlets")


def downgrade() -> None:
    """Remove outlets infrastructure."""

    # Drop foreign keys and indexes first
    op.drop_index('idx_import_batches_outlet', 'import_batches')
    op.drop_constraint('fk_import_batches_outlet', 'import_batches', type_='foreignkey')
    op.drop_column('import_batches', 'outlet_id')

    op.drop_index('idx_distributor_products_outlet', 'distributor_products')
    op.drop_constraint('fk_distributor_products_outlet', 'distributor_products', type_='foreignkey')
    op.drop_column('distributor_products', 'outlet_id')

    op.drop_index('idx_recipes_outlet', 'recipes')
    op.drop_constraint('fk_recipes_outlet', 'recipes', type_='foreignkey')
    op.drop_column('recipes', 'outlet_id')

    op.drop_index('idx_products_outlet', 'products')
    op.drop_constraint('fk_products_outlet', 'products', type_='foreignkey')
    op.drop_column('products', 'outlet_id')

    # Drop junction table
    op.drop_index('idx_user_outlets_outlet', 'user_outlets')
    op.drop_index('idx_user_outlets_user', 'user_outlets')
    op.drop_table('user_outlets')

    # Drop outlets table
    op.drop_index('idx_outlets_organization', 'outlets')
    op.drop_table('outlets')

    print("✅ Outlets infrastructure removed")

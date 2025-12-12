"""Add multi-tenancy support with organizations

Revision ID: d7d3ba15e17c
Revises: 001
Create Date: 2025-12-12 15:04:14.907970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7d3ba15e17c'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create organizations table
    op.create_table('organizations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('subscription_tier', sa.String(length=20), nullable=True, server_default='free'),
        sa.Column('subscription_status', sa.String(length=20), nullable=True, server_default='active'),
        sa.Column('max_users', sa.Integer(), nullable=True, server_default='2'),
        sa.Column('max_recipes', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint("subscription_tier IN ('free', 'basic', 'pro', 'enterprise')", name='check_subscription_tier'),
        sa.CheckConstraint("subscription_status IN ('active', 'inactive', 'suspended')", name='check_subscription_status'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Add organization_id to users table
    op.add_column('users', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_organization', 'users', 'organizations', ['organization_id'], ['id'])
    op.create_index('idx_users_organization', 'users', ['organization_id'])

    # Add organization_id to products table
    op.add_column('products', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_products_organization', 'products', 'organizations', ['organization_id'], ['id'])
    op.create_index('idx_products_organization', 'products', ['organization_id'])

    # Add organization_id to common_products table
    op.add_column('common_products', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_common_products_organization', 'common_products', 'organizations', ['organization_id'], ['id'])
    op.create_index('idx_common_products_organization', 'common_products', ['organization_id'])

    # Add organization_id to recipes table
    op.add_column('recipes', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_recipes_organization', 'recipes', 'organizations', ['organization_id'], ['id'])
    op.create_index('idx_recipes_organization', 'recipes', ['organization_id'])

    # Add organization_id to distributor_products table
    op.add_column('distributor_products', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_distributor_products_organization', 'distributor_products', 'organizations', ['organization_id'], ['id'])
    op.create_index('idx_distributor_products_organization', 'distributor_products', ['organization_id'])

    # Add organization_id to import_batches table
    op.add_column('import_batches', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_import_batches_organization', 'import_batches', 'organizations', ['organization_id'], ['id'])
    op.create_index('idx_import_batches_organization', 'import_batches', ['organization_id'])

    # Update unique constraint for distributor_products to include organization_id
    op.drop_constraint('unique_distributor_sku', 'distributor_products', type_='unique')
    op.create_unique_constraint('unique_distributor_sku_per_org', 'distributor_products',
                               ['organization_id', 'distributor_id', 'distributor_sku'])

    # Update unique constraint for common_products to include organization_id
    op.drop_constraint('common_products_common_name_key', 'common_products', type_='unique')
    op.create_unique_constraint('unique_common_name_per_org', 'common_products',
                               ['organization_id', 'common_name'])


def downgrade() -> None:
    """Downgrade schema."""
    # Restore original unique constraints
    op.drop_constraint('unique_common_name_per_org', 'common_products', type_='unique')
    op.create_unique_constraint('common_products_common_name_key', 'common_products', ['common_name'])

    op.drop_constraint('unique_distributor_sku_per_org', 'distributor_products', type_='unique')
    op.create_unique_constraint('unique_distributor_sku', 'distributor_products',
                               ['distributor_id', 'distributor_sku'])

    # Remove indexes
    op.drop_index('idx_import_batches_organization', table_name='import_batches')
    op.drop_index('idx_distributor_products_organization', table_name='distributor_products')
    op.drop_index('idx_recipes_organization', table_name='recipes')
    op.drop_index('idx_common_products_organization', table_name='common_products')
    op.drop_index('idx_products_organization', table_name='products')
    op.drop_index('idx_users_organization', table_name='users')

    # Remove foreign keys
    op.drop_constraint('fk_import_batches_organization', 'import_batches', type_='foreignkey')
    op.drop_constraint('fk_distributor_products_organization', 'distributor_products', type_='foreignkey')
    op.drop_constraint('fk_recipes_organization', 'recipes', type_='foreignkey')
    op.drop_constraint('fk_common_products_organization', 'common_products', type_='foreignkey')
    op.drop_constraint('fk_products_organization', 'products', type_='foreignkey')
    op.drop_constraint('fk_users_organization', 'users', type_='foreignkey')

    # Remove organization_id columns
    op.drop_column('import_batches', 'organization_id')
    op.drop_column('distributor_products', 'organization_id')
    op.drop_column('recipes', 'organization_id')
    op.drop_column('common_products', 'organization_id')
    op.drop_column('products', 'organization_id')
    op.drop_column('users', 'organization_id')

    # Drop organizations table
    op.drop_table('organizations')

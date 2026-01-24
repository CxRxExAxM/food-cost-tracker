"""Add vessels support

Create vessels table for organization-wide vessel definitions,
vessel_product_capacities for product-specific capacities,
and add vessel references to banquet_prep_items.

Revision ID: 011
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================
    # Table 1: vessels
    # Organization-wide vessel definitions
    # ============================================
    op.create_table('vessels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('default_capacity', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('default_unit_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Integer(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_vessels_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['default_unit_id'], ['units.id'],
                                name='fk_vessels_default_unit', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='unique_vessel_per_org')
    )

    # Indexes for vessels
    op.create_index('idx_vessels_org', 'vessels', ['organization_id'])
    op.create_index('idx_vessels_active', 'vessels', ['is_active'])

    # ============================================
    # Table 2: vessel_product_capacities
    # Product-specific capacities for vessels
    # ============================================
    op.create_table('vessel_product_capacities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vessel_id', sa.Integer(), nullable=False),
        sa.Column('common_product_id', sa.Integer(), nullable=False),
        sa.Column('capacity', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['vessel_id'], ['vessels.id'],
                                name='fk_vessel_capacities_vessel', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['common_product_id'], ['common_products.id'],
                                name='fk_vessel_capacities_common_product', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'],
                                name='fk_vessel_capacities_unit', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vessel_id', 'common_product_id', name='unique_vessel_product_capacity')
    )

    # Indexes for vessel_product_capacities
    op.create_index('idx_vessel_capacities_vessel', 'vessel_product_capacities', ['vessel_id'])
    op.create_index('idx_vessel_capacities_product', 'vessel_product_capacities', ['common_product_id'])

    # ============================================
    # Add vessel references to banquet_prep_items
    # ============================================
    op.add_column('banquet_prep_items',
        sa.Column('vessel_id', sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        'fk_banquet_prep_items_vessel',
        'banquet_prep_items', 'vessels',
        ['vessel_id'], ['id'],
        ondelete='SET NULL'
    )

    op.create_index(
        'idx_banquet_prep_items_vessel',
        'banquet_prep_items',
        ['vessel_id']
    )

    # Add vessel_count column
    op.add_column('banquet_prep_items',
        sa.Column('vessel_count', sa.Numeric(precision=10, scale=2), nullable=True)
    )

    print("✅ Vessels infrastructure created")


def downgrade():
    # Remove vessel columns from banquet_prep_items
    op.drop_column('banquet_prep_items', 'vessel_count')
    op.drop_index('idx_banquet_prep_items_vessel', 'banquet_prep_items')
    op.drop_constraint('fk_banquet_prep_items_vessel', 'banquet_prep_items', type_='foreignkey')
    op.drop_column('banquet_prep_items', 'vessel_id')

    # Drop vessel_product_capacities
    op.drop_index('idx_vessel_capacities_product', 'vessel_product_capacities')
    op.drop_index('idx_vessel_capacities_vessel', 'vessel_product_capacities')
    op.drop_table('vessel_product_capacities')

    # Drop vessels
    op.drop_index('idx_vessels_active', 'vessels')
    op.drop_index('idx_vessels_org', 'vessels')
    op.drop_table('vessels')

    print("✅ Vessels infrastructure removed")

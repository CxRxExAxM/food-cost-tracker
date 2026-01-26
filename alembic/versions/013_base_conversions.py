"""Add base_conversions table for standard unit conversions

Create base_conversions table for organization/outlet-level unit conversions.
These are standard conversions (OZ → LB, GAL → QT) that can be customized
per organization or outlet.

Revision ID: 013
Revises: 012
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================
    # Table: base_conversions
    # Standard unit conversions (not product-specific)
    # ============================================
    op.create_table('base_conversions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # NULL organization_id = system default (applies to all orgs)
        sa.Column('organization_id', sa.Integer(), nullable=True),
        # NULL outlet_id = applies to entire organization
        sa.Column('outlet_id', sa.Integer(), nullable=True),
        sa.Column('from_unit_id', sa.Integer(), nullable=False),
        sa.Column('to_unit_id', sa.Integer(), nullable=False),
        sa.Column('conversion_factor', sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), server_default='1', nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name='fk_base_conversions_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['outlet_id'], ['outlets.id'],
                                name='fk_base_conversions_outlet', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_unit_id'], ['units.id'],
                                name='fk_base_conversions_from_unit', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_unit_id'], ['units.id'],
                                name='fk_base_conversions_to_unit', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'],
                                name='fk_base_conversions_created_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Index for fast lookups (not unique due to NULL handling issues)
    op.create_index('idx_base_conversions_lookup',
                    'base_conversions',
                    ['organization_id', 'outlet_id', 'from_unit_id', 'to_unit_id'])
    op.create_index('idx_base_conversions_org', 'base_conversions', ['organization_id'])
    op.create_index('idx_base_conversions_outlet', 'base_conversions', ['outlet_id'])
    op.create_index('idx_base_conversions_units', 'base_conversions', ['from_unit_id', 'to_unit_id'])

    # ============================================
    # Seed system-wide default conversions
    # These apply to all organizations (organization_id = NULL)
    # Using individual INSERTs to avoid CASE/NULL issues
    # ============================================

    # Weight conversions
    weight_conversions = [
        ('OZ', 'LB', 0.0625),
        ('OZ', 'G', 28.3495),
        ('OZ', 'KG', 0.0283495),
        ('LB', 'OZ', 16),
        ('LB', 'G', 453.592),
        ('LB', 'KG', 0.453592),
        ('G', 'OZ', 0.035274),
        ('G', 'LB', 0.00220462),
        ('G', 'KG', 0.001),
        ('KG', 'OZ', 35.274),
        ('KG', 'LB', 2.20462),
        ('KG', 'G', 1000),
    ]

    for from_unit, to_unit, factor in weight_conversions:
        op.execute(f"""
            INSERT INTO base_conversions (organization_id, outlet_id, from_unit_id, to_unit_id, conversion_factor, notes)
            SELECT NULL, NULL, f.id, t.id, {factor}, 'System default weight conversion'
            FROM units f, units t
            WHERE f.abbreviation = '{from_unit}' AND t.abbreviation = '{to_unit}'
        """)

    # Volume conversions
    volume_conversions = [
        ('FL OZ', 'CUP', 0.125),
        ('FL OZ', 'PT', 0.0625),
        ('FL OZ', 'QT', 0.03125),
        ('FL OZ', 'GAL', 0.0078125),
        ('FL OZ', 'ML', 29.5735),
        ('FL OZ', 'L', 0.0295735),
        ('FL OZ', 'TBSP', 2),
        ('FL OZ', 'TSP', 6),
        ('GAL', 'FL OZ', 128),
        ('GAL', 'CUP', 16),
        ('GAL', 'PT', 8),
        ('GAL', 'QT', 4),
        ('GAL', 'ML', 3785.41),
        ('GAL', 'L', 3.78541),
        ('QT', 'FL OZ', 32),
        ('QT', 'CUP', 4),
        ('QT', 'PT', 2),
        ('QT', 'GAL', 0.25),
        ('QT', 'ML', 946.353),
        ('QT', 'L', 0.946353),
        ('PT', 'FL OZ', 16),
        ('PT', 'CUP', 2),
        ('PT', 'QT', 0.5),
        ('PT', 'GAL', 0.125),
        ('CUP', 'FL OZ', 8),
        ('CUP', 'PT', 0.5),
        ('CUP', 'QT', 0.25),
        ('CUP', 'GAL', 0.0625),
        ('CUP', 'ML', 236.588),
        ('CUP', 'TBSP', 16),
        ('CUP', 'TSP', 48),
        ('TBSP', 'FL OZ', 0.5),
        ('TBSP', 'TSP', 3),
        ('TBSP', 'ML', 14.7868),
        ('TBSP', 'CUP', 0.0625),
        ('TSP', 'FL OZ', 0.166667),
        ('TSP', 'TBSP', 0.333333),
        ('TSP', 'ML', 4.92892),
        ('TSP', 'CUP', 0.0208333),
        ('L', 'FL OZ', 33.814),
        ('L', 'ML', 1000),
        ('L', 'GAL', 0.264172),
        ('L', 'QT', 1.05669),
        ('ML', 'FL OZ', 0.033814),
        ('ML', 'L', 0.001),
        ('ML', 'TSP', 0.202884),
        ('ML', 'TBSP', 0.067628),
    ]

    for from_unit, to_unit, factor in volume_conversions:
        op.execute(f"""
            INSERT INTO base_conversions (organization_id, outlet_id, from_unit_id, to_unit_id, conversion_factor, notes)
            SELECT NULL, NULL, f.id, t.id, {factor}, 'System default volume conversion'
            FROM units f, units t
            WHERE f.abbreviation = '{from_unit}' AND t.abbreviation = '{to_unit}'
        """)

    print("✅ Base conversions table created and seeded with system defaults")


def downgrade():
    op.drop_index('idx_base_conversions_units', 'base_conversions')
    op.drop_index('idx_base_conversions_outlet', 'base_conversions')
    op.drop_index('idx_base_conversions_org', 'base_conversions')
    op.drop_index('idx_base_conversions_lookup', 'base_conversions')
    op.drop_table('base_conversions')

    print("✅ Base conversions table removed")
